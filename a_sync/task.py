"""
This module provides asynchronous task management utilities, specifically focused on creating and handling mappings of tasks.

The main components include:
- TaskMapping: A class for managing and asynchronously generating tasks based on input iterables.
- TaskMappingKeys: A view to asynchronously iterate over the keys of a TaskMapping.
- TaskMappingValues: A view to asynchronously iterate over the values of a TaskMapping.
- TaskMappingItems: A view to asynchronously iterate over the items (key-value pairs) of a TaskMapping.
"""

from asyncio import FIRST_COMPLETED, Future, Task, sleep, wait
from functools import wraps
from inspect import getfullargspec, isawaitable
from itertools import filterfalse
from logging import getLogger
from weakref import WeakKeyDictionary, proxy

from a_sync import exceptions
from a_sync._typing import *
from a_sync.a_sync._kwargs import _get_flag_name
from a_sync.a_sync.base import ASyncGenericBase
from a_sync.a_sync.function import ASyncFunction
from a_sync.a_sync.method import (
    ASyncBoundMethod,
    ASyncMethodDescriptor,
    ASyncMethodDescriptorSyncDefault,
)
from a_sync.a_sync.property import _ASyncPropertyDescriptorBase
from a_sync.asyncio import as_completed, create_task, gather
from a_sync.asyncio.gather import Excluder
from a_sync.asyncio.sleep import sleep0
from a_sync.functools import cached_property_unsafe
from a_sync.iter import ASyncIterator, ASyncGeneratorFunction, ASyncSorter
from a_sync.primitives.locks import Event
from a_sync.primitives.queue import Queue, ProcessingQueue
from a_sync.utils.iterators import as_yielded, exhaust_iterator
from a_sync.utils.repr import repr_trunc


logger = getLogger(__name__)


MappingFn = Callable[Concatenate[K, P], Awaitable[V]]


class TaskMapping(DefaultDict[K, "Task[V]"], AsyncIterable[Tuple[K, V]]):
    """
    A mapping of keys to asynchronous tasks with additional functionality.

    `TaskMapping` is a specialized dictionary that maps keys to `asyncio` Tasks. It provides
    convenient methods for creating, managing, and iterating over these tasks asynchronously.

    Tasks are created automatically for each key using a provided function. You cannot manually set items in a `TaskMapping` using dictionary-like syntax.

    Example:
        >>> async def fetch_data(url: str) -> str:
        ...     async with aiohttp.ClientSession() as session:
        ...         async with session.get(url) as response:
        ...             return await response.text()
        ...
        >>> tasks = TaskMapping(fetch_data, ['http://example.com', 'https://www.python.org'], name='url_fetcher', concurrency=5)
        >>> async for key, result in tasks:
        ...     print(f"Data for {key}: {result}")
        ...
        Data for python.org: http://python.org
        Data for example.com: http://example.com

    Note:
        You cannot manually set items in a `TaskMapping` using dictionary-like syntax. Tasks are created and managed internally.

    See Also:
        - :class:`asyncio.Task`
        - :func:`asyncio.create_task`
        - :func:`a_sync.asyncio.create_task`
    """

    concurrency: Optional[int] = None
    "The max number of tasks that will run at one time."

    _destroyed: bool = False
    "Boolean indicating whether his mapping has been consumed and is no longer usable for aggregations."

    _init_loader: Optional["Task[None]"] = None
    "An asyncio Task used to preload values from the iterables."

    _init_loader_next: Optional[Callable[[], Awaitable[Tuple[Tuple[K, "Task[V]"]]]]] = None
    "A coro function that blocks until the _init_loader starts a new task(s), and then returns a `Tuple[Tuple[K, Task[V]]]` with all of the new tasks and the keys that started them."

    _name: Optional[str] = None
    "Optional name for tasks created by this mapping."

    _next: Event = None
    "An asyncio Event that indicates the next result is ready"

    _wrapped_func_kwargs: Dict[str, Any] = {}
    "Additional keyword arguments passed to `_wrapped_func`."

    __iterables__: Tuple[AnyIterableOrAwaitableIterable[K], ...] = ()
    "The original iterables, if any, used to initialize this mapping."

    __init_loader_coro: Optional[Awaitable[None]] = None
    """An optional asyncio Coroutine to be run by the `_init_loader`"""

    __slots__ = "_wrapped_func", "__wrapped__", "__dict__", "__weakref__"

    # NOTE: maybe since we use so many classvars here we are better off getting rid of slots
    def __init__(
        self,
        wrapped_func: MappingFn[K, P, V] = None,
        *iterables: AnyIterableOrAwaitableIterable[K],
        name: str = "",
        concurrency: Optional[int] = None,
        **wrapped_func_kwargs: P.kwargs,
    ) -> None:
        """
        Initialize a TaskMapping instance.

        Args:
            wrapped_func: A callable that takes a key and additional parameters and returns an Awaitable.
            *iterables: Any number of iterables whose elements will be used as keys for task generation.
            name: An optional name for the tasks created by this mapping.
            concurrency: Maximum number of tasks to run concurrently.
            **wrapped_func_kwargs: Additional keyword arguments to be passed to wrapped_func.

        Example:
            async def process_item(item: int) -> int:
                await asyncio.sleep(1)
                return item * 2

            task_map = TaskMapping(process_item, [1, 2, 3], concurrency=2)
        """

        if concurrency:
            self.concurrency = concurrency

        self.__wrapped__ = wrapped_func
        "The original callable used to initialize this mapping without any modifications."

        if iterables:
            self.__iterables__ = iterables

        wrapped_func = _unwrap(wrapped_func)
        self._wrapped_func = wrapped_func
        "The function used to create tasks for each key."

        if isinstance(wrapped_func, ASyncMethodDescriptor) and not _get_flag_name(
            wrapped_func_kwargs
        ):
            wrapped_func_kwargs["sync"] = False
        if wrapped_func_kwargs:
            self._wrapped_func_kwargs = wrapped_func_kwargs

        if name:
            self._name = name

        self._next = Event(name=f"{self} `_next`")

        if iterables:

            @wraps(wrapped_func)
            async def _wrapped_set_next(
                *args: P.args, __a_sync_recursion: int = 0, **kwargs: P.kwargs
            ) -> V:
                try:
                    return await wrapped_func(*args, **kwargs)
                except exceptions.SyncModeInAsyncContextError as e:
                    e.args = *e.args, f"wrapped:{self.__wrapped__}"
                    raise
                except TypeError as e:
                    if __a_sync_recursion > 2 or not (
                        str(e).startswith(wrapped_func.__name__)
                        and "got multiple values for argument" in str(e)
                    ):
                        raise
                    # NOTE: args ordering is clashing with provided kwargs. We can handle this in a hacky way.
                    # TODO: perform this check earlier and pre-prepare the args/kwargs ordering
                    new_args = list(args)
                    new_kwargs = dict(kwargs)
                    try:
                        for i, arg in enumerate(getfullargspec(self.__wrapped__).args):
                            if arg in kwargs:
                                new_args.insert(i, new_kwargs.pop(arg))
                            else:
                                break
                        return await _wrapped_set_next(
                            *new_args,
                            **new_kwargs,
                            __a_sync_recursion=__a_sync_recursion + 1,
                        )
                    except TypeError as e2:
                        raise (
                            e.with_traceback(e.__traceback__)
                            if str(e2) == "unsupported callable"
                            else e2.with_traceback(e2.__traceback__)
                        )
                finally:
                    self._next.set()
                    self._next.clear()

            self._wrapped_func = _wrapped_set_next
            init_loader_queue: Queue[Tuple[K, "Future[V]"]] = Queue()
            self.__init_loader_coro = exhaust_iterator(
                self._start_tasks_for_iterables(*iterables), queue=init_loader_queue
            )
            self._init_loader_next = init_loader_queue.get_all

            try:
                self._init_loader
            except _NoRunningLoop:
                # its okay if we get this exception, we can start the task as soon as the loop starts
                pass

    def __repr__(self) -> str:
        return f"<{type(self).__name__} for {self._wrapped_func} kwargs={self._wrapped_func_kwargs} tasks={len(self)} at {hex(id(self))}>"

    def __hash__(self) -> int:
        return id(self)

    def __setitem__(self, item: Any, value: Any) -> None:
        raise NotImplementedError("You cannot manually set items in a TaskMapping")

    def __getitem__(self, item: K) -> "Task[V]":
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            return self.__start_task(item)

    def __await__(self) -> Generator[Any, None, Dict[K, V]]:
        """Wait for all tasks to complete and return a dictionary of the results."""
        return self.gather(sync=False).__await__()

    async def __aiter__(self, pop: bool = False) -> AsyncIterator[Tuple[K, V]]:
        # sourcery skip: hoist-loop-from-if, hoist-similar-statement-from-if, hoist-statement-from-if
        """Asynchronously iterate through all key-task pairs, yielding the key-result pair as each task completes."""

        self._if_pop_check_destroyed(pop)

        # if you inited the TaskMapping with some iterators, we will load those
        yielded = set()
        add_yielded = yielded.add
        try:
            if self._init_loader is None:
                # if you didn't init the TaskMapping with iterators and you didn't start any tasks manually, we should fail
                self._raise_if_empty()
            else:
                while not self._init_loader.done():
                    await self._wait_for_next_key()
                    while unyielded := tuple(key for key in self if key not in yielded):
                        if ready := tuple(key for key in unyielded if self[key].done()):
                            if pop:
                                self_pop = self.pop
                                for key in ready:
                                    yield key, self_pop(key).result()
                                    add_yielded(key)
                            else:
                                for key in ready:
                                    yield key, self[key].result()
                                    add_yielded(key)
                        else:
                            await self._next.wait()
                # loader is already done by this point, but we need to check for exceptions
                await self._init_loader
            # if there are any tasks that still need to complete, we need to await them and yield them
            if unyielded := {key: self[key] for key in self if key not in yielded}:
                if pop:
                    self_pop = self.pop
                    async for key, value in as_completed(unyielded, aiter=True):
                        self_pop(key)
                        yield key, value
                else:
                    async for key, value in as_completed(unyielded, aiter=True):
                        yield key, value
        finally:
            await self._if_pop_clear(pop)

    def __delitem__(self, item: K) -> None:
        task_or_fut = dict.__getitem__(self, item)
        if not task_or_fut.done():
            task_or_fut.cancel()
        dict.__delitem__(self, item)

    def keys(self, pop: bool = False) -> "TaskMappingKeys[K, V]":
        return TaskMappingKeys(dict.keys(self), self, pop=pop)

    def values(self, pop: bool = False) -> "TaskMappingValues[K, V]":
        return TaskMappingValues(dict.values(self), self, pop=pop)

    def items(self, pop: bool = False) -> "TaskMappingValues[K, V]":
        return TaskMappingItems(dict.items(self), self, pop=pop)

    async def close(self) -> None:
        await self._if_pop_clear(True)

    @ASyncGeneratorFunction
    async def map(
        self,
        *iterables: AnyIterableOrAwaitableIterable[K],
        pop: bool = True,
        yields: Literal["keys", "both"] = "both",
    ) -> AsyncIterator[Tuple[K, V]]:
        # sourcery skip: hoist-similar-statement-from-if
        """
        Asynchronously map iterables to tasks and yield their results.

        Args:
            *iterables: Iterables to map over.
            pop: Whether to remove tasks from the internal storage once they are completed.
            yields: Whether to yield 'keys', 'values', or 'both' (key-value pairs).

        Yields:
            Depending on `yields`, either keys, values,
            or tuples of key-value pairs representing the results of completed tasks.

        Example:
            async def process_item(item: int) -> int:
                await asyncio.sleep(1)
                return item * 2

            task_map = TaskMapping(process_item)
            async for key, result in task_map.map([1, 2, 3]):
                print(f"Processed {key}: {result}")
        """
        self._if_pop_check_destroyed(pop)

        # make sure the init loader is started if needed
        init_loader = self._init_loader
        if iterables and init_loader:
            raise ValueError(
                "You cannot pass `iterables` to map if the TaskMapping was initialized with an (a)iterable."
            )

        try:
            if iterables:
                self._raise_if_not_empty()

                def callback(t: Task):
                    self._next.set()

                try:
                    async for k, t in self._tasks_for_iterables(*iterables):
                        t.add_done_callback(callback)
                        if self._next.is_set():
                            async for key, value in self.yield_completed(pop=pop):
                                yield _yield(key, value, yields)
                            self._next.clear()
                except _EmptySequenceError:
                    if len(iterables) > 1:
                        # TODO gotta handle this situation
                        raise exceptions.EmptySequenceError(
                            "bob needs to code something so you can do this, go tell him"
                        ) from None
                    # just pass thru
                finally:
                    self._next.clear()

            elif init_loader:
                # check for exceptions if you passed an iterable(s) into the class init
                await init_loader

            else:
                self._raise_if_empty(
                    "You must either initialize your TaskMapping with an iterable(s) or provide them during your call to map"
                )

            if self:
                if pop:
                    self_pop = self.pop
                    async for key, value in as_completed(self, aiter=True):
                        self_pop(key)
                        yield _yield(key, value, yields)
                else:
                    async for key, value in as_completed(self, aiter=True):
                        yield _yield(key, value, yields)
        finally:
            await self._if_pop_clear(pop)

    @ASyncMethodDescriptorSyncDefault
    async def all(self, pop: bool = True) -> bool:
        try:
            async for key, result in self.__aiter__(pop=pop):
                if not bool(result):
                    return False
            return True
        except _EmptySequenceError:
            return True
        finally:
            await self._if_pop_clear(pop)

    @ASyncMethodDescriptorSyncDefault
    async def any(self, pop: bool = True) -> bool:
        try:
            async for key, result in self.__aiter__(pop=pop):
                if bool(result):
                    return True
            return False
        except _EmptySequenceError:
            return False
        finally:
            await self._if_pop_clear(pop)

    @ASyncMethodDescriptorSyncDefault
    async def max(self, pop: bool = True) -> V:
        # sourcery skip: avoid-builtin-shadow
        max = None
        try:
            async for key, result in self.__aiter__(pop=pop):
                if max is None or result > max:
                    max = result
        except _EmptySequenceError:
            raise exceptions.EmptySequenceError("max() arg is an empty sequence") from None
        if max is None:
            raise exceptions.EmptySequenceError("max() arg is an empty sequence") from None
        return max

    @ASyncMethodDescriptorSyncDefault
    async def min(self, pop: bool = True) -> V:
        # sourcery skip: avoid-builtin-shadow
        """Return the minimum result from the tasks in the mapping."""
        min = None
        try:
            async for key, result in self.__aiter__(pop=pop):
                if min is None or result < min:
                    min = result
        except _EmptySequenceError:
            raise exceptions.EmptySequenceError("min() arg is an empty sequence") from None
        if min is None:
            raise exceptions.EmptySequenceError("min() arg is an empty sequence") from None
        return min

    @ASyncMethodDescriptorSyncDefault
    async def sum(self, pop: bool = False) -> V:
        """Return the sum of the results from the tasks in the mapping."""
        retval = 0
        try:
            async for key, result in self.__aiter__(pop=pop):
                retval += result
        except _EmptySequenceError:
            return 0
        return retval

    @ASyncIterator.wrap
    async def yield_completed(self, pop: bool = True) -> AsyncIterator[Tuple[K, V]]:
        """
        Asynchronously yield tuples of key-value pairs representing the results of any completed tasks.

        Args:
            pop: Whether to remove tasks from the internal storage once they are completed.

        Yields:
            Tuples of key-value pairs representing the results of completed tasks.

        Example:
            async def process_item(item: int) -> int:
                await asyncio.sleep(1)
                return item * 2

            task_map = TaskMapping(process_item, [1, 2, 3])
            async for key, result in task_map.yield_completed():
                print(f"Completed {key}: {result}")
        """
        task: Task
        if pop:
            self_pop = self.pop
            for k in tuple(k for k, task in dict.items(self) if task.done()):
                yield k, self_pop(k).result()
        else:
            for k, task in dict.items(self):
                if task.done():
                    yield k, task.result()

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
        self._raise_if_empty()
        return await gather(
            self,
            return_exceptions=return_exceptions,
            exclude_if=exclude_if,
            tqdm=tqdm,
            **tqdm_kwargs,
        )

    @overload
    def pop(self, item: K, *, cancel: bool = False) -> "Union[Task[V], Future[V]]":
        """Pop a task from the TaskMapping.

        Args:
            item: The key to pop.
            cancel: Whether to cancel the task when popping it.
        """

    @overload
    def pop(self, item: K, default: K, *, cancel: bool = False) -> "Union[Task[V], Future[V]]":
        """Pop a task from the TaskMapping.

        Args:
            item: The key to pop.
            default: The default value to return if no matching key is found.
            cancel: Whether to cancel the task when popping it.
        """

    def pop(self, *args: K, cancel: bool = False) -> "Union[Task[V], Future[V]]":
        """Pop a task from the TaskMapping.

        Args:
            *args: One key to pop.
            cancel: Whether to cancel the task when popping it.
        """
        fut_or_task = dict.pop(self, *args)
        if cancel:
            fut_or_task.cancel()
        return fut_or_task

    def clear(self, cancel: bool = False) -> None:
        """# TODO write docs for this"""
        if cancel and self._init_loader and not self._init_loader.done():
            logger.debug("cancelling %s", self._init_loader)
            self._init_loader.cancel()
        if keys := tuple(self.keys()):
            logger.debug("popping remaining %s tasks", self)
            pop = self.pop
            for k in keys:
                pop(k, cancel=cancel)

    @cached_property_unsafe
    def _init_loader(self) -> Optional["Task[None]"]:
        # sourcery skip: raise-from-previous-error
        if self.__init_loader_coro is None:
            return None

        logger.debug("starting %s init loader", self)
        if len(iterables := self.__iterables__) == 1:
            iterables_repr = repr_trunc(iterables[0])
        else:
            iterables_repr = f"({', '.join(map(repr_trunc, iterables))})"
        try:
            task = create_task(
                coro=self.__init_loader_coro,
                name=f"{type(self).__name__} init loader loading {iterables_repr} for {self}",
            )
        except RuntimeError as e:
            raise _NoRunningLoop if str(e) == "no running event loop" else e
        task.add_done_callback(self.__cleanup)
        return task

    @cached_property_unsafe
    def _queue(self) -> ProcessingQueue:
        fn = lambda arg: self._wrapped_func(arg, **self._wrapped_func_kwargs)
        return ProcessingQueue(fn, self.concurrency, name=self._name)

    def _raise_if_empty(self, msg: str = "") -> None:
        if not self:
            raise exceptions.MappingIsEmptyError(self, msg)

    def _raise_if_not_empty(self) -> None:
        if self:
            raise exceptions.MappingNotEmptyError(self)

    @ASyncGeneratorFunction
    async def _tasks_for_iterables(
        self, *iterables: AnyIterableOrAwaitableIterable[K]
    ) -> AsyncIterator[Tuple[K, "Task[V]"]]:
        """Ensure tasks are running for each key in the provided iterables."""
        # if we have any regular containers we can yield their contents right away
        containers = tuple(
            iterable
            for iterable in iterables
            if not isinstance(iterable, AsyncIterable) and isinstance(iterable, Iterable)
        )
        for iterable in containers:
            async for key in _yield_keys(iterable):
                yield key, self[key]

        if remaining := tuple(iterable for iterable in iterables if iterable not in containers):
            try:
                async for key in as_yielded(*(_yield_keys(iterable) for iterable in remaining)):  # type: ignore [attr-defined]
                    yield key, self[key]  # ensure task is running
            except _EmptySequenceError:
                if len(iterables) == 1:
                    raise
                raise RuntimeError("DEV: figure out how to handle this situation") from None

    @ASyncGeneratorFunction
    async def _start_tasks_for_iterables(
        self, *iterables: AnyIterableOrAwaitableIterable[K]
    ) -> AsyncIterator[Tuple[K, "Task[V]"]]:
        """Start new tasks for each key in the provided iterables."""
        # if we have any regular containers we can yield their contents right away
        containers = tuple(
            iterable
            for iterable in iterables
            if not isinstance(iterable, AsyncIterable) and isinstance(iterable, Iterable)
        )
        for iterable in containers:
            async for key in _yield_keys(iterable):
                yield key, self.__start_task(key)

        if remaining := tuple(iterable for iterable in iterables if iterable not in containers):
            try:
                async for key in as_yielded(*(_yield_keys(iterable) for iterable in remaining)):  # type: ignore [attr-defined]
                    yield key, self.__start_task(key)
            except _EmptySequenceError:
                if len(iterables) == 1:
                    raise
                raise RuntimeError("DEV: figure out how to handle this situation") from None

    def _if_pop_check_destroyed(self, pop: bool) -> None:
        if pop:
            if self._destroyed:
                raise RuntimeError(f"{self} has already been consumed")
            self._destroyed = True

    async def _if_pop_clear(self, pop: bool) -> None:
        if pop:
            self._destroyed = True
            # _queue is a cached_property, we don't want to create it if it doesn't exist
            if self.concurrency and "_queue" in self.__dict__:
                self._queue.close()
                del self._queue
            self.clear(cancel=True)
            # we need to let the loop run once so the tasks can fully cancel
            await sleep0()

    async def _wait_for_next_key(self) -> None:
        # NOTE if `_init_loader` has an exception it will return first, otherwise `_init_loader_next` will return always
        done, pending = await wait(
            (
                create_task(self._init_loader_next(), log_destroy_pending=False),
                self._init_loader,
            ),
            return_when=FIRST_COMPLETED,
        )
        task: Task
        for task in done:
            # check for exceptions
            task.result()

    def __start_task(self, item: K) -> "Future[V]":
        if self.concurrency:
            # NOTE: we use a queue instead of a Semaphore to reduce memory use for use cases involving many many tasks
            fut = self._queue.put_nowait(item)
        else:
            fut = create_task(
                coro=self._wrapped_func(item, **self._wrapped_func_kwargs),
                name=f"{item}" if self._name is None else f"{self._name}[{item}]",
            )
        dict.__setitem__(self, item, fut)
        return fut

    def __cleanup(self, t: "Task[None]") -> None:
        # clear the slot and let the bound Queue die
        del self.__init_loader_coro


class _NoRunningLoop(Exception): ...


@overload
def _yield(
    key: K, value: V, yields: Literal["keys"]
) -> K: ...  # TODO write specific docs for this overload
@overload
def _yield(
    key: K, value: V, yields: Literal["both"]
) -> Tuple[K, V]: ...  # TODO write specific docs for this overload
def _yield(key: K, value: V, yields: Literal["keys", "both"]) -> Union[K, Tuple[K, V]]:
    """
    Yield either the key, value, or both based on the 'yields' parameter.

    Args:
        key: The key of the task.
        value: The result of the task.
        yields: Determines what to yield; 'keys' for keys, 'both' for key-value pairs.

    Returns:
        The key, the value, or a tuple of both based on the 'yields' parameter.
    """
    if yields == "both":
        return key, value
    elif yields == "keys":
        return key
    else:
        raise ValueError(f"`yields` must be 'keys' or 'both'. You passed {yields}")


class _EmptySequenceError(ValueError): ...


async def _yield_keys(iterable: AnyIterableOrAwaitableIterable[K]) -> AsyncIterator[K]:
    """
    Asynchronously yield keys from the provided iterable.

    Args:
        iterable: An iterable that can be either synchronous or asynchronous.

    Yields:
        Keys extracted from the iterable.
    """
    if not iterable:
        raise _EmptySequenceError(iterable)

    elif isinstance(iterable, AsyncIterable):
        async for key in iterable:
            yield key

    elif isinstance(iterable, Iterable):
        yielded = 0

        async def unblock_loop() -> None:
            nonlocal yielded
            yielded += 1
            if not yielded % 1000:  # arbitrary number, should be adjusted later
                await sleep0()

        for key in iterable:
            yield key
            await unblock_loop()

    elif isawaitable(iterable):
        async for key in _yield_keys(await iterable):
            yield key

    else:
        raise TypeError(iterable)


__unwrapped = WeakKeyDictionary()


def _unwrap(
    wrapped_func: Union[
        AnyFn[P, T], "ASyncMethodDescriptor[P, T]", _ASyncPropertyDescriptorBase[I, T]
    ],
) -> Callable[P, Awaitable[T]]:
    if unwrapped := __unwrapped.get(wrapped_func):
        return unwrapped
    if isinstance(wrapped_func, (ASyncBoundMethod, ASyncMethodDescriptor)):
        unwrapped = wrapped_func
    elif isinstance(wrapped_func, _ASyncPropertyDescriptorBase):
        unwrapped = wrapped_func.get
    elif isinstance(wrapped_func, ASyncFunction):
        # this speeds things up a bit by bypassing some logic
        # TODO implement it like this elsewhere if profilers suggest
        unwrapped = (
            wrapped_func._modified_fn if wrapped_func._async_def else wrapped_func._asyncified
        )
    else:
        unwrapped = wrapped_func
    __unwrapped[wrapped_func] = unwrapped
    return unwrapped


_get_key: Callable[[Tuple[K, V]], K] = lambda k_and_v: k_and_v[0]
_get_value: Callable[[Tuple[K, V]], V] = lambda k_and_v: k_and_v[1]


class _TaskMappingView(ASyncGenericBase, Iterable[T], Generic[T, K, V]):
    """
    Base class for TaskMapping views that provides common functionality.
    """

    _get_from_item: Callable[[Tuple[K, V]], T]
    _pop: bool = False

    __slots__ = "__view__", "__mapping__"

    def __init__(
        self, view: Iterable[T], task_mapping: TaskMapping[K, V], pop: bool = False
    ) -> None:
        self.__view__ = view
        self.__mapping__: TaskMapping = proxy(task_mapping)
        "actually a weakref.ProxyType[TaskMapping] but then type hints weren't working"
        if pop:
            self._pop = True

    def __iter__(self) -> Iterator[T]:
        return iter(self.__view__)

    def __await__(self) -> Generator[Any, None, List[T]]:
        return self.__await().__await__()

    def __len__(self) -> int:
        return len(self.__view__)

    async def aiterbykeys(self, reverse: bool = False) -> ASyncIterator[T]:
        async for tup in ASyncSorter(
            self.__mapping__.items(pop=self._pop), key=_get_key, reverse=reverse
        ):
            yield self._get_from_item(tup)

    async def aiterbyvalues(self, reverse: bool = False) -> ASyncIterator[T]:
        async for tup in ASyncSorter(
            self.__mapping__.items(pop=self._pop), key=_get_value, reverse=reverse
        ):
            yield self._get_from_item(tup)

    async def __await(self) -> List[T]:
        return [result async for result in self]


class TaskMappingKeys(_TaskMappingView[K, K, V], Generic[K, V]):
    """
    Asynchronous view to iterate over the keys of a TaskMapping.
    """

    _get_from_item = lambda self, item: _get_key(item)

    async def __aiter__(self) -> AsyncIterator[K]:
        # strongref
        mapping = self.__mapping__
        mapping._if_pop_check_destroyed(self._pop)
        yielded = set()
        add_yielded = yielded.add
        for key in self.__load_existing():
            add_yielded(key)
            # there is no chance of duplicate keys here
            yield key
        if mapping._init_loader is None:
            await mapping._if_pop_clear(self._pop)
            return
        async for key in self.__load_init_loader(yielded):
            add_yielded(key)
            yield key
        if self._pop:
            # don't need to check yielded since we've been popping them as we go
            for key in self.__load_existing():
                yield key
            await mapping._if_pop_clear(True)
        else:
            for key in self.__load_existing():
                if key not in yielded:
                    yield key

    def __load_existing(self) -> Iterator[K]:
        # strongref
        mapping = self.__mapping__
        if self._pop:
            pop = mapping.pop
            for key in tuple(mapping):
                pop(key)
                yield key
        else:
            yield from tuple(mapping)

    async def __load_init_loader(self, yielded: Set[K]) -> AsyncIterator[K]:
        # sourcery skip: hoist-loop-from-if
        # strongref
        mapping = self.__mapping__
        done = mapping._init_loader.done
        wait_for_next_key = mapping._wait_for_next_key

        if self._pop:
            pop = mapping.pop
            while not done():
                await wait_for_next_key()
                for key in tuple(filterfalse(yielded.__contains__, mapping)):
                    pop(key)
                    yield key
        else:
            while not done():
                await wait_for_next_key()
                for key in tuple(filterfalse(yielded.__contains__, mapping)):
                    yield key
        # check for any exceptions
        await mapping._init_loader


class TaskMappingItems(_TaskMappingView[Tuple[K, V], K, V], Generic[K, V]):
    """
    Asynchronous view to iterate over the items (key-value pairs) of a TaskMapping.
    """

    _get_from_item = lambda self, item: item

    async def __aiter__(self) -> AsyncIterator[Tuple[K, V]]:
        # strongref
        mapping = self.__mapping__
        mapping._if_pop_check_destroyed(self._pop)
        if self._pop:
            pop = mapping.pop
            async for key in mapping.keys():
                yield key, await pop(key)
        else:
            async for key in mapping.keys():
                yield key, await mapping[key]


class TaskMappingValues(_TaskMappingView[V, K, V], Generic[K, V]):
    """
    Asynchronous view to iterate over the values of a TaskMapping.
    """

    _get_from_item = lambda self, item: _get_value(item)

    async def __aiter__(self) -> AsyncIterator[V]:
        # strongref
        mapping = self.__mapping__
        mapping._if_pop_check_destroyed(self._pop)
        if self._pop:
            pop = mapping.pop
            async for key in mapping.keys():
                yield await pop(key)
        else:
            async for key in mapping.keys():
                yield await mapping[key]


__all__ = [
    "TaskMapping",
    "TaskMappingKeys",
    "TaskMappingValues",
    "TaskMappingItems",
]
