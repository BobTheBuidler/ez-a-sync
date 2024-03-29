
import asyncio
import logging

from a_sync._typing import *
from a_sync import exceptions
from a_sync.iter import ASyncIterable
from a_sync.utils.as_completed import as_completed
from a_sync.utils.gather import gather
from a_sync.utils.iterators import as_yielded, exhaust_iterator


logger = logging.getLogger(__name__)

def create_task(coro: Awaitable[T], *, name: Optional[str] = None, skip_gc_until_done: bool = False) -> "asyncio.Task[T]":

    """A wrapper over `asyncio.create_task` which will work with any `Awaitable` object, not just `Coroutine` objects"""

    """
    Extends asyncio.create_task to support any Awaitable, manage task lifecycle, and enhance error handling.

    Unlike asyncio.create_task, which requires a coroutine, this function accepts any Awaitable, ensuring broader
    compatibility. It optionally prevents the task from being garbage-collected until completion and provides
    enhanced error management by wrapping exceptions in a custom exception.

    Args:
        coro: An Awaitable object from which to create the task.
        name: Optional name for the task, aiding in debugging.
        skip_gc_until_done: If True, the task is kept alive until it completes, preventing garbage collection.

    Returns:
        An asyncio.Task object created from the provided Awaitable.
    """

    if not asyncio.iscoroutine(coro):
        coro = __await(coro)
    task = asyncio.create_task(coro, name=name)
    if skip_gc_until_done:
        __persist(asyncio.create_task(__persisted_task_exc_wrap(task)))
    return task


MappingFn = Callable[Concatenate[K, P], Awaitable[V]]

class TaskMapping(ASyncIterable[Tuple[K, V]], Mapping[K, "asyncio.Task[V]"]):
    """
    A mapping from keys to asyncio Tasks that asynchronously generates and manages tasks based on input iterables.
    
    Attributes:
        _wrapped_func: The function used to generate values for each key.
        _wrapped_func_kwargs: Additional keyword arguments passed to `_wrapped_func`.
        _name: Optional name for tasks created by this mapping.
        _tasks: Internal storage for the tasks.
        _init_loader: An asyncio Task used to preload values from the iterables.
    
    Args:
        wrapped_func: A function that takes a key (and optional parameters) and returns an Awaitable.
        *iterables: Any number of iterables whose elements will be used as keys for task generation.
        name: An optional name for the tasks created by this mapping.
        **wrapped_func_kwargs: Keyword arguments that will be passed to `wrapped_func`.
    """
    __slots__ = "_wrapped_func", "_wrapped_func_kwargs", "_name", "_tasks", "_init_loader"
    
    def __init__(self, wrapped_func: MappingFn[K, P, V] = None, *iterables: AnyIterable[K], name: str = '', **wrapped_func_kwargs: P.kwargs) -> None:
        self._wrapped_func = wrapped_func
        self._wrapped_func_kwargs = wrapped_func_kwargs
        self._name = name
        self._tasks: Dict[K, "asyncio.Task[V]"] = {}
        self._init_loader: Optional["asyncio.Task[None]"]
        if iterables:
            self._init_loader = create_task(exhaust_iterator(self._tasks_for_iterables(*iterables)))
        else:
            self._init_loader = None
    
    def __repr__(self) -> str:
        return f"<{type(self).__name__} for {self._wrapped_func} ({self._tasks}) at {hex(id(self))}>"
    
    def __setitem__(self, item: Any, value: Any) -> None:
        raise NotImplementedError("You cannot manually set items in a TaskMapping")
    
    def __getitem__(self, item: K) -> "asyncio.Task[V]":
        try:
            return self._tasks[item]
        except KeyError:
            task = create_task(
                coro=self._wrapped_func(item, **self._wrapped_func_kwargs),
                name=f"{self._name}[{item}]" if self._name else f"{item}",
            )
            self._tasks[item] = task
            return task
    
    def __len__(self) -> int:
        return len(self._tasks)
    
    def __await__(self) -> Generator[Any, None, Dict[K, V]]:
        """Wait for all tasks to complete and return a dictionary of the results."""
        return self._await().__await__()
    
    async def __aiter__(self) -> AsyncIterator[Tuple[K, V]]:
        """aiterate thru all key-task pairs, yielding the key-result pair as each task completes"""
        yielded = set()
        # if you inited the TaskMapping with some iterators, we will load those
           
        if self._init_loader:
            while not self._init_loader.done():
                async for key, value in self.yield_completed(pop=False):
                    if key not in yielded:
                        yield _yield(key, value, "both")
                        yielded.add(key)
                await asyncio.sleep(0)
            # loader is already done by this point, but we need to check for exceptions
            await self._init_loader
        elif not self:
            # if you didn't init the TaskMapping with iterators and you didn't start any tasks manually, we should fail
            raise exceptions.MappingIsEmptyError
        # if there are any tasks that still need to complete, we need to await them and yield them
        if self:
            async for key, value in as_completed(self._tasks, aiter=True):
                if key not in yielded:
                    yield _yield(key, value, "both")
    async def map(self, *iterables: AnyIterable[K], pop: bool = True, yields: Literal['keys', 'both'] = 'both') -> AsyncIterator[Tuple[K, V]]:
        """
            Asynchronously map iterables to tasks and yield their results.

            Args:
            *iterables: Iterables to map over.
            pop: Whether to remove tasks from the internal storage once they are completed.
            yields: Whether to yield 'keys', 'values', or 'both' (key-value pairs).
        
            Yields:
            Depending on `yields`, either keys, values,
            or tuples of key-value pairs representing the results of completed tasks.
        """
        if self:
            raise exceptions.MappingNotEmptyError
        else:
            logger.info(self)
        async for _ in self._tasks_for_iterables(*iterables):
            async for key, value in self.yield_completed(pop=pop):
                yield _yield(key, value, yields)
        async for key, value in as_completed(self._tasks, aiter=True):
            if pop:
                self._tasks.pop(key)
            yield _yield(key, value, yields)
    
    async def yield_completed(self, pop: bool = True) -> AsyncIterator[Tuple[K, V]]:
        """
        Asynchronously yield tuples of key-value pairs representing the results of any completed tasks.

        Args:
            pop: Whether to remove tasks from the internal storage once they are completed.

        Yields:
            Tuples of key-value pairs representing the results of completed tasks.
        """
        for k, task in dict(self._tasks).items():
            if task.done():
                if pop:
                    task = self._tasks.pop(k)
                yield k, await task
    
    async def _await(self) -> Dict[K, V]:
        """Wait for all tasks to complete and return a dictionary of the results."""
        if self._init_loader:
            await self._init_loader
        if not self:
            raise exceptions.MappingIsEmptyError
        return await gather(self)
    
    async def _tasks_for_iterables(self, *iterables) -> AsyncIterator["asyncio.Task[V]"]:
        """Ensure tasks are running for each key in the provided iterables."""
        async for key in as_yielded(*[_yield_keys(iterable) for iterable in iterables]): # type: ignore [attr-defined]
            yield self[key]  # ensure task is running


__persisted_tasks: Set["asyncio.Task[Any]"] = set()

async def __await(awaitable: Awaitable[T]) -> T:
    """Wait for the completion of an Awaitable."""
    return await awaitable
    
def __persist(task: "asyncio.Task[Any]") -> None:
    """Add a task to the set of persisted tasks."""
    __persisted_tasks.add(task)
    __prune_persisted_tasks()

def __prune_persisted_tasks():
    """Remove completed tasks from the set of persisted tasks."""
    for task in tuple(__persisted_tasks):
        if task.done():
            if (e := task.exception()) and not isinstance(e, exceptions.PersistedTaskException):
                logger.exception(e)
                raise e
            __persisted_tasks.discard(task)

async def __persisted_task_exc_wrap(task: "asyncio.Task[T]") -> T:
    """
    Wrap a task to handle its exception in a specialized manner.

    Args:
        task: The asyncio Task to wrap.

    Returns:
        The result of the task, if successful.

    Raises:
        PersistedTaskException: Wraps any exception raised by the task for special handling.
    """
    try:
        return await task
    except Exception as e:
        raise exceptions.PersistedTaskException(e, task) from e

@overload
def _yield(key: K, value: V, yields: Literal['keys']) -> K:...
@overload
def _yield(key: K, value: V, yields: Literal['both']) -> Tuple[K, V]:...
def _yield(key: K, value: V, yields: Literal['keys', 'both']) -> Union[K, Tuple[K, V]]:
    """
    Yield either the key, value, or both based on the 'yields' parameter.
    
    Args:
        key: The key of the task.
        value: The result of the task.
        yields: Determines what to yield; 'keys' for keys, 'both' for key-value pairs.
    
    Returns:
        The key, the value, or a tuple of both based on the 'yields' parameter.
    """
    if yields == 'both':
        return key, value
    elif yields == 'keys':
        return key
    else:
        raise ValueError(f"`yields` must be 'keys' or 'both'. You passed {yields}")
    
async def _yield_keys(iterable: AnyIterable[K]) -> AsyncIterator[K]:
    """
    Asynchronously yield keys from the provided iterable.

    Args:
        iterable: An iterable that can be either synchronous or asynchronous.

    Yields:
        Keys extracted from the iterable.
    """
    if isinstance(iterable, AsyncIterable):
        async for key in iterable:
            yield key
    elif isinstance(iterable, Iterable):
        for key in iterable:
            yield key
    else:
        raise TypeError(iterable)
