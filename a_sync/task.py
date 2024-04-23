
import asyncio
import functools
import inspect
import logging

from a_sync import _kwargs
from a_sync._bound import ASyncBoundMethod, ASyncMethodDescriptor, ASyncMethodDescriptorSyncDefault
from a_sync._typing import *
from a_sync import exceptions
from a_sync.base import ASyncGenericBase
from a_sync.iter import ASyncIterator, ASyncGeneratorFunction
from a_sync.modified import ASyncFunction
from a_sync.primitives.queue import Queue, ProcessingQueue
from a_sync.property import _ASyncPropertyDescriptorBase
from a_sync.utils.as_completed import as_completed
from a_sync.utils.gather import Excluder, gather
from a_sync.utils.iterators import as_yielded, exhaust_iterator


logger = logging.getLogger(__name__)

def create_task(coro: Awaitable[T], *, name: Optional[str] = None, skip_gc_until_done: bool = False) -> "asyncio.Task[T]":
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

class TaskMapping(DefaultDict[K, "asyncio.Task[V]"], AsyncIterable[Tuple[K, V]]):
    """
    A mapping from keys to asyncio Tasks that asynchronously generates and manages tasks based on input iterables.
    """
    
    _destroyed: bool = False
    "Boolean indicating whether his mapping has been consumed and is no longer usable for aggregations."

    _init_loader: Optional["asyncio.Task[None]"] = None
    "An asyncio Task used to preload values from the iterables."

    _init_loader_next: Optional[Callable[[], Awaitable[Tuple[K, V]]]] = None
    "An asyncio Event that indicates the _init_loader started a new task."
    
    __init_loader_coro: Optional[Awaitable[None]] = None
    """An optional asyncio Coroutine to be run by the `_init_loader`"""

    __slots__ = "concurrency", "_wrapped_func", "_wrapped_func_kwargs", "_name", "_next", "__wrapped__", "__dict__"
    def __init__(
        self, 
        wrapped_func: MappingFn[K, P, V] = None, 
        *iterables: AnyIterableOrAwaitableIterable[K], 
        name: str = '', 
        concurrency: Optional[int] = None, 
        **wrapped_func_kwargs: P.kwargs,
    ) -> None:
        """
        Args:
            wrapped_func: A function that takes a key (and optional parameters) and returns an Awaitable.
            *iterables: Any number of iterables whose elements will be used as keys for task generation.
            name: An optional name for the tasks created by this mapping.
            **wrapped_func_kwargs: Keyword arguments that will be passed to `wrapped_func`.
        """

        self.concurrency = concurrency
        "The max number of coroutines that will run at any given time."

        self.__wrapped__ = wrapped_func
        "The original callable used to initialize this mapping without any modifications."""

        wrapped_func = _unwrap(wrapped_func)
        self._wrapped_func = wrapped_func
        "The function used to generate values for each key."

        if isinstance(wrapped_func, ASyncMethodDescriptor):
            if _kwargs.get_flag_name(wrapped_func_kwargs) is None:
                wrapped_func_kwargs["sync"] = False
        self._wrapped_func_kwargs = wrapped_func_kwargs
        "Additional keyword arguments passed to `_wrapped_func`."

        self._name = name
        "Optional name for tasks created by this mapping."

        if iterables:
            self._next = asyncio.Event()
            "An asyncio Event that indicates the next result is ready"
            @functools.wraps(wrapped_func)
            async def _wrapped_set_next(*args: P.args, __a_sync_recursion: int = 0, **kwargs: P.kwargs) -> V:
                try:
                    retval = await wrapped_func(*args, **kwargs)
                    self._next.set()
                    self._next.clear()
                    return retval
                except exceptions.SyncModeInAsyncContextError as e:
                    raise Exception(e, self.__wrapped__)
                except TypeError as e:
                    if recursion > 2 or not (str(e).startswith(wrapped_func.__name__) and "got multiple values for argument" in str(e)):
                        raise e
                    # NOTE: args ordering is clashing with provided kwargs. We can handle this in a hacky way.
                    # TODO: perform this check earlier and pre-prepare the args/kwargs ordering
                    new_args = list(args)
                    new_kwargs = dict(kwargs)
                    try:
                        for i, arg in enumerate(inspect.getfullargspec(self.__wrapped__).args):
                            if arg in kwargs:
                                new_args.insert(i, new_kwargs.pop(arg))
                            else:
                                break
                        return await _wrapped_set_next(*new_args, **new_kwargs, __a_sync_recursion=__a_sync_recursion+1)
                    except TypeError as e2:
                        raise e if str(e2) == "unsupported callable" else e2
            self._wrapped_func = _wrapped_set_next
            init_loader_queue: Queue[Tuple[K, "asyncio.Future[V]"]] = Queue()
            init_loader_coro = exhaust_iterator(self._tasks_for_iterables(*iterables), queue=init_loader_queue)
            try:
                self._init_loader = create_task(init_loader_coro)
            except RuntimeError as e:
                if str(e) != "no running event loop":
                    raise e
                # its okay, we can start it as soon as the loop starts
                self.__init_loader_coro = init_loader_coro
            self._init_loader_next = init_loader_queue.get_all
        else:
            self._init_loader = None
    
    def __repr__(self) -> str:
        return f"<{type(self).__name__} for {self._wrapped_func} ({dict.__repr__(self)}) at {hex(id(self))}>"
    
    def __hash__(self) -> int:
        return id(self)
    
    def __setitem__(self, item: Any, value: Any) -> None:
        raise NotImplementedError("You cannot manually set items in a TaskMapping")
    
    def __getitem__(self, item: K) -> "asyncio.Task[V]":
        try:
            return super().__getitem__(item)
        except KeyError:
            try:
                if self.concurrency:
                    # NOTE: we use a queue instead of a Semaphore to reduce memory use for use cases involving many many tasks
                    fut = self._queue.put_nowait(item)
                else:
                    coro = self._wrapped_func(item, **self._wrapped_func_kwargs)
                    name = f"{self._name}[{item}]" if self._name else f"{item}",
                    fut = create_task(coro=coro, name=name)
                super().__setitem__(item, fut)
                return fut
            except Exception as e:
                raise e from None
        
    def __await__(self) -> Generator[Any, None, Dict[K, V]]:
        """Wait for all tasks to complete and return a dictionary of the results."""
        return self.gather(sync=False).__await__()

    async def __aiter__(self, pop: bool = False) -> AsyncIterator[Tuple[K, V]]:
        """aiterate thru all key-task pairs, yielding the key-result pair as each task completes"""
        yielded = set()
        # if you inited the TaskMapping with some iterators, we will load those
           
        if self._init_loader:
            while not self._init_loader.done():
                await self._init_loader_next()
                while unyielded := [key for key in self if key not in yielded]:
                    if ready := {key: task for key in unyielded if (task:=self[key]).done()}:
                        for key, task in ready.items():
                            self._if_pop_pop(pop, key)
                            yield key, await task
                            yielded.add(key)
                    else:
                        await self._next.wait()
            # loader is already done by this point, but we need to check for exceptions
            await self._init_loader
        else:
            # if you didn't init the TaskMapping with iterators and you didn't start any tasks manually, we should fail
            self._check_empty()
        # if there are any tasks that still need to complete, we need to await them and yield them
        if unyielded := {key: self[key] for key in self if key not in yielded}:
            async for key, value in as_completed(unyielded, aiter=True):
                self._if_pop_pop(pop, key)
                yield key, value

    def __delitem__(self, item: K) -> None:
        task_or_fut = super().__getitem__(item)
        if task_or_fut.done():
            task_or_fut.cancel()
        super().__delitem__(item)

    def keys(self) -> "TaskMappingKeys[K, V]":
        return TaskMappingKeys(super().keys(), self)

    def values(self) -> "TaskMappingValues[K, V]":
        return TaskMappingValues(super().values(), self)
    
    def items(self) -> "TaskMappingValues[K, V]":
        return TaskMappingItems(super().items(), self)
    
    @ASyncGeneratorFunction
    async def map(self, *iterables: AnyIterableOrAwaitableIterable[K], pop: bool = True, yields: Literal['keys', 'both'] = 'both') -> AsyncIterator[Tuple[K, V]]:
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
        self._check_not_empty()
        async for _ in self._tasks_for_iterables(*iterables):
            async for key, value in self.yield_completed(pop=pop):
                yield _yield(key, value, yields)
        async for key, value in as_completed(self, aiter=True):
            self._if_pop_pop(pop, key)
            yield _yield(key, value, yields)
    
    @ASyncMethodDescriptorSyncDefault
    async def all(self, pop: bool = True) -> bool:
        self._if_pop_check_destroyed(pop)
        async for key, result in self.__aiter__(pop=pop):
            if not bool(result):
                self._if_pop_clear(pop)
                return False
        return True
    
    @ASyncMethodDescriptorSyncDefault
    async def any(self, pop: bool = True) -> bool:
        self._if_pop_check_destroyed(pop)
        async for key, result in self.__aiter__(pop=pop):
            if bool(result):
                self._if_pop_clear(pop)
                return True
        return False
    
    @ASyncMethodDescriptorSyncDefault
    async def max(self, pop: bool = True) -> V:
        self._if_pop_check_destroyed(pop)
        max = None
        async for key, result in self.__aiter__(pop=pop):
            if max is None or result > max:
                max = result
        if min is None:
            raise ValueError("we should not get here")
        return max
    
    @ASyncMethodDescriptorSyncDefault
    async def min(self, pop: bool = True) -> V:
        self._if_pop_check_destroyed(pop)
        min = None
        async for key, result in self.__aiter__(pop=pop):
            if min is None or result < min:
                min = result
        if min is None:
            raise ValueError("we should not get here")
        return min
            
    @ASyncMethodDescriptorSyncDefault
    async def sum(self, pop: bool = False) -> V:
        self._if_pop_check_destroyed(pop)
        retval = None
        async for key, result in self.__aiter__(pop=pop):
            if retval is None:
                retval = 0 + result
            else:
                retval += result
        if retval is None:
            raise ValueError("we should not get here")
        return result

    @ASyncIterator.wrap
    async def yield_completed(self, pop: bool = True) -> AsyncIterator[Tuple[K, V]]:
        """
        Asynchronously yield tuples of key-value pairs representing the results of any completed tasks.

        Args:
            pop: Whether to remove tasks from the internal storage once they are completed.

        Yields:
            Tuples of key-value pairs representing the results of completed tasks.
        """
        for k, task in dict(self).items():
            if task.done():
                self._if_pop_pop(pop, k)
                yield k, await task
    
    @ASyncMethodDescriptorSyncDefault
    async def gather(
        self, 
        return_exceptions: bool = False, 
        exclude_if: Excluder[V] = None,
        tqdm: bool = False,
        **tqdm_kwargs: Any,
    ) -> Dict[K, V]:
        """Wait for all tasks to complete and return a dictionary of the results."""
        if self._init_loader:
            await self._init_loader
        self._check_empty()
        return await gather(self, return_exceptions=return_exceptions, exclude_if=exclude_if, tqdm=tqdm, **tqdm_kwargs)
    
    @overload
    def pop(self, item: K, cancel: bool = False) -> "Union[asyncio.Task[V], asyncio.Future[V]]":...
    @overload
    def pop(self, item: K, default: K, cancel: bool = False) -> "Union[asyncio.Task[V], asyncio.Future[V]]":...
    def pop(self, *args: K, cancel: bool = False) -> "Union[asyncio.Task[V], asyncio.Future[V]]":
        if not cancel:
            return super().pop(*args)
        fut_or_task = super().pop(*args)
        if isinstance(fut_or_task, asyncio.Future) and not fut_or_task.done():
            fut_or_task.cancel()
        return fut_or_task
    
    def clear(self, cancel: bool = False) -> None:
        for k in self:
            self.pop(k, cancel=cancel)

    @functools.cached_property
    def _init_loader(self) -> "asyncio.Task[None]":
        return create_task(self.__init_loader_coro)
    
    @functools.cached_property
    def _queue(self) -> ProcessingQueue:
        fn = functools.partial(self._wrapped_func, **self._wrapped_func_kwargs)
        return ProcessingQueue(fn, self.concurrency)
    
    def _if_pop_check_destroyed(self, pop: bool) -> None:
        if pop:
            if self._destroyed:
                raise RuntimeError(f"{self} has already been consumed")
            self._destroyed = True
    
    def _if_pop_clear(self, pop: bool) -> None:
        if pop:
            self.clear(cancel=True)
    
    @overload
    def _if_pop_pop(self, pop: bool, key: K, cancel: bool = False) -> None:...
    @overload
    def _if_pop_pop(self, pop: bool, key: K, default: T, cancel: bool = False) -> None:...
    def _if_pop_pop(self, pop: bool, *args: K, cancel: bool = False) -> None:
        if pop:
            self.pop(*args, cancel=cancel)
    
    def _check_empty(self) -> None:
        if not self:
            raise exceptions.MappingIsEmptyError
    
    def _check_not_empty(self) -> None:
        if self:
            raise exceptions.MappingNotEmptyError

    @ASyncGeneratorFunction
    async def _tasks_for_iterables(self, *iterables: AnyIterableOrAwaitableIterable[K]) -> AsyncIterator[Tuple[K, "asyncio.Task[V]"]]:
        """Ensure tasks are running for each key in the provided iterables."""
        async for key in as_yielded(*[_yield_keys(iterable) for iterable in iterables]): # type: ignore [attr-defined]
            yield key, self[key]  # ensure task is running


__persisted_tasks: Set["asyncio.Task[Any]"] = set()

async def __await(awaitable: Awaitable[T]) -> T:
    """Wait for the completion of an Awaitable."""
    try:
        return await awaitable
    except RuntimeError as e:
        args = [e, awaitable]
        if isinstance(awaitable, asyncio.tasks._GatheringFuture):
            args.append(awaitable._children)
        raise RuntimeError(*args) from None

    
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
    
async def _yield_keys(iterable: AnyIterableOrAwaitableIterable[K]) -> AsyncIterator[K]:
    """
    Asynchronously yield keys from the provided iterable.

    Args:
        iterable: An iterable that can be either synchronous or asynchronous.

    Yields:
        Keys extracted from the iterable.
    """
    if not iterable:
        raise ValueError(iterable)
    elif isinstance(iterable, AsyncIterable):
        async for key in iterable:
            yield key
    elif isinstance(iterable, Iterable):
        for key in iterable:
            yield key
    elif inspect.isawaitable(iterable):
        async for key in _yield_keys(await iterable):
            yield key
    else:
        raise TypeError(iterable)

@functools.lru_cache(maxsize=None)
def _unwrap(wrapped_func: Union[AnyFn[P, T], "ASyncMethodDescriptor[P, T]", _ASyncPropertyDescriptorBase[I, T]]) -> Callable[P, Awaitable[T]]:
    if isinstance(wrapped_func, (ASyncBoundMethod, ASyncMethodDescriptor)):
        return wrapped_func
    elif isinstance(wrapped_func, _ASyncPropertyDescriptorBase):
        return wrapped_func.get
    elif isinstance(wrapped_func, ASyncFunction):
        # this speeds things up a bit by bypassing some logic
        # TODO implement it like this elsewhere if profilers suggest
        return wrapped_func._modified_fn if wrapped_func._async_def else wrapped_func._asyncified
    return wrapped_func


class _TaskMappingView(ASyncGenericBase, Iterable[T], Generic[T, K, V]):
    def __init__(self, view: Iterable[T], task_mapping: TaskMapping[K, V]) -> None:
        self.__view__ = view
        self.__mapping__ = task_mapping
    def __iter__(self) -> Iterator[T]:
        return iter(self.__view__)
    def __await__(self) -> List[T]:
        return self._await().__await__()
    def __len__(self) -> int:
        return len(self.__view__)
    async def _await(self) -> List[T]:
        return [result async for result in self]
    __slots__ = "__view__", "__mapping__"


class TaskMappingKeys(_TaskMappingView[K, K, V], Generic[K, V]):
    async def __aiter__(self) -> AsyncIterator[K]:
        yielded = set()
        for key in self.__mapping__:
            yielded.add(key)
            yield key
        if self.__mapping__._init_loader is None:
            return
        while not self.__mapping__._init_loader.done():
            for key, fut in await self.__mapping__._init_loader_next():
                if key not in yielded:
                    yielded.add(key)
                    yield key
        if e := self.__mapping__._init_loader.exception():
            raise e
        for key in self.__mapping__:
            if key not in yielded:
                yield key

class TaskMappingItems(_TaskMappingView[Tuple[K, V], K, V], Generic[K, V]):
    async def __aiter__(self) -> AsyncIterator[Tuple[K, V]]:
        async for key in self.__mapping__.keys():
            yield key, await self.__mapping__[key]
    
class TaskMappingValues(_TaskMappingView[V, K, V], Generic[K, V]):
    async def __aiter__(self) -> AsyncIterator[V]:
        async for key in self.__mapping__.keys():
            yield await self.__mapping__[key]
