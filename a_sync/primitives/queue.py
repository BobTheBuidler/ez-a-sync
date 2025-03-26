"""
This module provides various queue implementations for managing asynchronous tasks.
It includes standard FIFO queues, priority queues, and processing queues with enhanced functionality.

Classes:
    Queue: A generic asynchronous queue that extends the functionality of `asyncio.Queue`.
    ProcessingQueue: A queue designed for processing tasks asynchronously with multiple workers.
    PriorityProcessingQueue: A priority-based processing queue where tasks are processed based on priority.
    SmartProcessingQueue: A processing queue that executes jobs with the most waiters first, supporting dynamic priorities.

See Also:
    `asyncio.Queue`: The base class for asynchronous FIFO queues.
    `asyncio.PriorityQueue`: The base class for priority queues.
"""

import asyncio
import sys
from asyncio import AbstractEventLoop, Future, InvalidStateError, QueueEmpty, Task, get_event_loop
from asyncio.events import _get_running_loop
from functools import wraps
from heapq import heappop, heappush, heappushpop
from logging import getLogger
from weakref import WeakValueDictionary, proxy, ref

from a_sync._smart import SmartFuture, create_future
from a_sync._smart import _Key as _SmartKey
from a_sync._typing import *
from a_sync.asyncio import create_task, igather
from a_sync.functools import cached_property_unsafe

logger = getLogger(__name__)
log_debug = logger.debug

if sys.version_info < (3, 9):

    class _Queue(asyncio.Queue, Generic[T]):
        __slots__ = (
            "_queue",
            "_maxsize",
            "_loop",
            "_getters",
            "_putters",
            "_unfinished_tasks",
            "_finished",
        )

else:

    class _Queue(asyncio.Queue[T]):
        __slots__ = (
            "_queue",
            "_maxsize",
            "_getters",
            "_putters",
            "_unfinished_tasks",
            "_finished",
        )


class Queue(_Queue[T]):
    """
    A generic asynchronous queue that extends the functionality of `asyncio.Queue`.

    This implementation supports retrieving multiple items at once and handling
    task processing in both FIFO and LIFO order. It provides enhanced type hinting
    support and additional methods for bulk operations.

    Inherits from:
        - :class:`~asyncio.Queue`

    Example:
        >>> queue = Queue()
        >>> await queue.put(item='task1')
        >>> await queue.put(item='task2')
        >>> result = await queue.get()
        >>> print(result)
        task1
        >>> all_tasks = await queue.get_all()
        >>> print(all_tasks)
        ['task2']
    """

    def __bool__(self) -> Literal[True]:
        """A Queue will always exist, even without items."""
        return True

    def __len__(self) -> int:
        """Returns the number of items currently in the queue."""
        return len(self._queue)

    async def get(self) -> T:
        """
        Asynchronously retrieves and removes the next item from the queue.

        If the queue is empty, this method will block until an item is available.

        Example:
            >>> result = await queue.get()
            >>> print(result)
        """
        return await _Queue.get(self)

    def get_nowait(self) -> T:
        """
        Retrieves and removes the next item from the queue without blocking.

        This method does not wait for an item to be available and will raise
        an exception if the queue is empty.

        Raises:
            :exc:`~asyncio.QueueEmpty`: If the queue is empty.

        Example:
            >>> result = queue.get_nowait()
            >>> print(result)
        """
        return _Queue.get_nowait(self)

    async def put(self, item: T) -> None:
        """
        Asynchronously adds an item to the queue.

        If the queue is full, this method will block until space is available.

        Args:
            item: The item to add to the queue.

        Example:
            >>> await queue.put(item='task')
        """
        await _Queue.put(self, item)

    def put_nowait(self, item: T) -> None:
        """
        Adds an item to the queue without blocking.

        This method does not wait for space to be available and will raise
        an exception if the queue is full.

        Args:
            item: The item to add to the queue.

        Raises:
            :exc:`~asyncio.QueueFull`: If the queue is full.

        Example:
            >>> queue.put_nowait(item='task')
        """
        return _Queue.put_nowait(self, item)

    async def get_all(self) -> List[T]:
        """
        Asynchronously retrieves and removes all available items from the queue.

        If the queue is empty, this method will wait until at least one item
        is available before returning.

        Example:
            >>> tasks = await queue.get_all()
            >>> print(tasks)
        """
        try:
            return self.get_all_nowait()
        except QueueEmpty:
            return [await self.get()]

    def get_all_nowait(self) -> List[T]:
        """
        Retrieves and removes all available items from the queue without waiting.

        This method does not wait for items to be available and will raise
        an exception if the queue is empty.

        Raises:
            :exc:`~asyncio.QueueEmpty`: If the queue is empty.

        Example:
            >>> tasks = queue.get_all_nowait()
            >>> print(tasks)
        """
        get_nowait = self.get_nowait
        values: List[T] = []
        append = values.append

        while True:
            try:
                append(get_nowait())
            except QueueEmpty as e:
                if not values:
                    raise QueueEmpty from e
                return values

    async def get_multi(self, i: int, can_return_less: bool = False) -> List[T]:
        """
        Asynchronously retrieves up to `i` items from the queue.

        Args:
            i: The number of items to retrieve.
            can_return_less: If True, may return fewer than `i` items if queue is emptied.

        Raises:
            :exc:`~asyncio.QueueEmpty`: If no items are available and fewer items cannot be returned.

        Example:
            >>> tasks = await queue.get_multi(i=2, can_return_less=True)
            >>> print(tasks)
        """
        _validate_args(i, can_return_less)
        get_next = self.get
        get_multi = self.get_multi_nowait

        items = []
        extend = items.extend
        while len(items) < i and not can_return_less:
            try:
                extend(get_multi(i - len(items), can_return_less=True))
            except QueueEmpty:
                items = [await get_next()]
        return items

    def get_multi_nowait(self, i: int, can_return_less: bool = False) -> List[T]:
        """
        Retrieves up to `i` items from the queue without waiting.

        Args:
            i: The number of items to retrieve.
            can_return_less: If True, may return fewer than `i` items if queue is emptied.

        Raises:
            :exc:`~asyncio.QueueEmpty`: If no items are available and fewer items cannot be returned.

        Example:
            >>> tasks = queue.get_multi_nowait(i=3, can_return_less=True)
            >>> print(tasks)
        """
        _validate_args(i, can_return_less)

        get_nowait = self.get_nowait

        items = []
        append = items.append
        for _ in range(i):
            try:
                append(get_nowait())
            except QueueEmpty:
                if items and can_return_less:
                    return items
                # put these back in the queue since we didn't return them
                put_nowait = self.put_nowait
                for value in items:
                    put_nowait(value)
                raise QueueEmpty from None
        return items


def log_broken(func: Callable[[Any], NoReturn]) -> Callable[[Any], NoReturn]:
    @wraps(func)
    async def __worker_exc_wrap(self: "ProcessingQueue"):
        try:
            return await func(self)
        except Exception as e:
            logger.error("%s is broken!!!", self)
            logger.exception(e)
            raise

    return __worker_exc_wrap


_init = asyncio.Queue.__init__
_put_nowait = asyncio.Queue.put_nowait
_loop_kwarg_deprecated = sys.version_info >= (3, 10)


class ProcessingQueue(_Queue[Tuple[P, "Future[V]"]], Generic[P, V]):
    """
    A queue designed for processing tasks asynchronously with multiple workers.

    Each item in the queue is processed by a worker, and tasks can return results
    via asynchronous futures. This queue is ideal for scenarios where tasks need
    to be processed concurrently with a fixed number of workers.

    Example:
        >>> async def process_task(data): return data.upper()
        >>> queue = ProcessingQueue(func=process_task, num_workers=5)
        >>> fut = await queue.put(item='task')
        >>> print(await fut)
        TASK
    """

    _closed: bool = False
    """Indicates whether the queue is closed."""

    __slots__ = "func", "num_workers"

    def __init__(
        self,
        func: Callable[P, Awaitable[V]],
        num_workers: int,
        *,
        return_data: bool = True,
        name: str = "",
        loop: Optional[AbstractEventLoop] = None,
    ) -> None:
        """
        Initializes a processing queue with the given worker function and worker count.

        Args:
            func: The task function to process.
            num_workers: Number of workers to process tasks.
            return_data: Whether tasks should return data via futures. Defaults to True.
            name: Name of the queue. Defaults to an empty string.
            loop: Optional event loop for the queue.

        Example:
            >>> queue = ProcessingQueue(func=my_task_func, num_workers=3, name='myqueue')
        """
        if not _loop_kwarg_deprecated:
            _init(self, loop=loop)
        elif loop:
            raise NotImplementedError(
                f"You cannot pass a value for `loop` in python {sys.version_info}"
            )
        else:
            _init(self)

        self.func = func
        """The function that each worker will process."""

        self.num_workers = num_workers
        """The number of worker tasks for processing."""

        self._name = name
        """Optional name for the queue."""

        self._no_futs = not return_data
        """Indicates whether tasks will return data via futures."""

    # NOTE: asyncio defines both this and __str__
    def __repr__(self) -> str:
        """
        Provides a detailed string representation of the queue.

        Example:
            >>> print(queue)
        """
        repr_string = f"<{type(self).__name__} at {hex(id(self))}"
        if self._name:
            repr_string += f" name={self._name}"
        repr_string += f" func={self.func} num_workers={self.num_workers}"
        if self._unfinished_tasks:
            repr_string += f" pending={self._unfinished_tasks}"
        return f"{repr_string}>"

    # NOTE: asyncio defines both this and __repr__
    def __str__(self) -> str:
        """
        Provides a string representation of the queue.

        Example:
            >>> print(queue)
        """
        repr_string = f"<{type(self).__name__}"
        if self._name:
            repr_string += f" name={self._name}"
        repr_string += f" func={self.func} num_workers={self.num_workers}"
        if self._unfinished_tasks:
            repr_string += f" pending={self._unfinished_tasks}"
        return f"{repr_string}>"

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> "Future[V]":
        """
        Submits a task to the queue.

        Example:
            >>> fut = queue(*args, **kwargs)
            >>> print(fut)
        """
        return self.put_nowait(*args, **kwargs)

    def __del__(self) -> None:
        """
        Handles the deletion of the queue, ensuring tasks are handled.
        """
        if self._closed:
            return
        if self._unfinished_tasks > 0:
            context = {
                "message": f"{self} was destroyed but has work pending!",
            }
            if loop := _get_running_loop():
                loop.call_exception_handler(context)

    @property
    def name(self) -> str:
        """
        Returns the name of the queue, or its representation.

        Example:
            >>> print(queue.name)
        """
        return self._name or repr(self)

    def close(self) -> None:
        """
        Closes the queue, preventing further task submissions.

        Example:
            >>> queue.close()
        """
        self._closed = True

    async def put(self, *args: P.args, **kwargs: P.kwargs) -> "Future[V]":
        # sourcery skip: use-contextlib-suppress
        """
        Asynchronously submits a task to the queue.

        Args:
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            The future result of the task.

        Example:
            >>> fut = await queue.put(item='task')
            >>> print(await fut)
        """
        while self.full():
            putter = self._get_loop().create_future()
            self._putters.append(putter)
            try:
                await putter
            except:
                putter.cancel()  # Just in case putter is not done yet.
                try:
                    # Clean self._putters from canceled putters.
                    self._putters.remove(putter)
                except ValueError:
                    # The putter could be removed from self._putters by a
                    # previous get_nowait call.
                    pass
                if not self.full() and not putter.cancelled():
                    # We were woken up by get_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._putters)
                raise
        return self.put_nowait(*args, **kwargs)

    def put_nowait(self, *args: P.args, **kwargs: P.kwargs) -> "Future[V]":
        """
        Immediately submits a task to the queue without waiting.

        Args:
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            The future result of the task.

        Example:
            >>> fut = queue.put_nowait(item='task')
            >>> print(await fut)
        """
        self._ensure_workers()
        if self._no_futs:
            return _put_nowait(self, (args, kwargs))
        fut = Future(loop=self._workers._loop)
        _put_nowait(self, (args, kwargs, proxy(fut)))
        return fut

    def _ensure_workers(self) -> None:
        """Ensures that the worker tasks are running."""
        if self._closed:
            raise RuntimeError(f"{type(self).__name__} is closed: ", self) from None
        if self._workers.done():
            worker_subtasks: List["Task[NoReturn]"] = self._workers._workers
            for worker in worker_subtasks:
                if worker.done():  # its only done if its broken
                    exc = worker.exception()
                    # re-raise with clean traceback
                    raise exc.with_traceback(exc.__traceback__) from exc.__cause__
            # this should never be reached, but just in case
            exc = self._workers.exception()
            # re-raise with clean traceback
            raise exc.with_traceback(exc.__traceback__) from exc.__cause__

    @cached_property_unsafe
    def _workers(self) -> "Task[NoReturn]":
        """Creates and manages the worker tasks for the queue."""
        log_debug("starting worker task for %s", self)
        name = str(self.name)
        workers = tuple(
            create_task(
                coro=self._worker_coro(),
                name=f"{name} [Task-{i}]",
                log_destroy_pending=False,
            )
            for i in range(self.num_workers)
        )
        task = create_task(
            igather(workers),
            name=f"{name} worker main Task",
            log_destroy_pending=False,
        )
        task._workers = workers
        return task

    @log_broken
    async def _worker_coro(self) -> NoReturn:
        """
        The coroutine executed by worker tasks to process the queue.
        """
        get_next_job = self.get
        func = self.func
        task_done = self.task_done

        args: P.args
        kwargs: P.kwargs
        if self._no_futs:
            while True:
                try:
                    args, kwargs = await get_next_job()
                    await func(*args, **kwargs)
                except Exception as e:
                    logger.error("%s in worker for %s!", type(e).__name__, self)
                    logger.exception(e)
                task_done()
        else:
            fut: Future[V]
            while True:
                try:
                    args, kwargs, fut = await get_next_job()
                except RuntimeError as e:
                    if _check_loop_is_closed(self, e):
                        return
                    raise

                if fut is None:
                    # the weakref was already cleaned up, we don't need to process this item
                    task_done()
                    continue

                try:
                    result = await func(*args, **kwargs)
                except Exception as e:
                    try:
                        fut.set_exception(e)
                    except InvalidStateError:
                        _log_invalid_state_err("exception", func, fut, e)
                else:
                    try:
                        fut.set_result(result)
                    except InvalidStateError:
                        _log_invalid_state_err("result", func, fut, result)
                task_done()


def _validate_args(i: int, can_return_less: bool) -> None:
    """
    Validates the arguments for methods that retrieve multiple items from the queue.

    Args:
        i: The number of items to retrieve.
        can_return_less: Whether the method is allowed to return fewer than `i` items.

    Raises:
        :exc:`~TypeError`: If `i` is not an integer or `can_return_less` is not a boolean.
        :exc:`~ValueError`: If `i` is not greater than 1.

    Example:
        >>> _validate_args(i=2, can_return_less=False)
    """
    if not isinstance(i, int):
        raise TypeError(f"`i` must be an integer greater than 1. You passed {i}")
    if not isinstance(can_return_less, bool):
        raise TypeError(f"`can_return_less` must be boolean. You passed {can_return_less}")
    if i <= 1:
        raise ValueError(f"`i` must be an integer greater than 1. You passed {i}")


class _SmartFutureRef(ref, Generic[T]):
    """
    Weak reference for :class:`~SmartFuture` objects used in priority queues.

    See Also:
        :class:`~SmartFuture`
    """

    def __lt__(self, other: "_SmartFutureRef[T]") -> bool:
        """
        Compares two weak references to SmartFuture objects for ordering.

        This comparison is used in priority queues to determine the order of processing. A SmartFuture
        reference is considered less than another if it has more waiters or if it has been garbage collected.

        Args:
            other: The other SmartFuture reference to compare with.

        Returns:
            bool: True if this reference is less than the other, False otherwise.

        Example:
            >>> ref1 = _SmartFutureRef(fut1)
            >>> ref2 = _SmartFutureRef(fut2)
            >>> print(ref1 < ref2)
        """
        strong_self = self()
        if strong_self is None:
            return True
        strong_other = other()
        if strong_other is None:
            return False
        return strong_self < strong_other


class _PriorityQueueMixin(Generic[T]):
    """
    Mixin for creating priority queue functionality with support for custom comparison.

    See Also:
        :class:`~asyncio.PriorityQueue`
    """

    def _init(self, maxsize):
        """
        Initializes the priority queue.

        Example:
            >>> queue._init(maxsize=10)
        """
        self._queue: List[T] = []

    def _put(self, item, heappush=heappush):
        """
        Adds an item to the priority queue based on its priority.

        Example:
            >>> queue._put(item='task')
        """
        heappush(self._queue, item)

    def _get(self, heappop=heappop):
        """
        Retrieves the highest priority item from the queue.

        Example:
            >>> task = queue._get()
            >>> print(task)
        """
        return heappop(self._queue)


class PriorityProcessingQueue(_PriorityQueueMixin[T], ProcessingQueue[T, V]):
    """
    A priority-based processing queue where tasks are processed based on priority.

    This queue allows tasks to be added with a specified priority, ensuring that
    higher priority tasks are processed before lower priority ones. It is ideal
    for scenarios where task prioritization is crucial.

    Example:
        >>> async def process_task(data): return data.upper()
        >>> queue = PriorityProcessingQueue(func=process_task, num_workers=5)
        >>> fut = await queue.put(priority=1, item='task')
        >>> print(await fut)
        TASK

    See Also:
        :class:`~ProcessingQueue`
    """

    async def put(self, priority: Any, *args: P.args, **kwargs: P.kwargs) -> "Future[V]":
        # sourcery skip: use-contextlib-suppress
        """
        Asynchronously adds a task with priority to the queue.

        Args:
            priority: The priority of the task.
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            The future representing the result of the task.

        Example:
            >>> fut = await queue.put(priority=1, item='task')
            >>> print(await fut)
        """
        while self.full():
            putter = self._get_loop().create_future()
            self._putters.append(putter)
            try:
                await putter
            except:
                putter.cancel()  # Just in case putter is not done yet.
                try:
                    # Clean self._putters from canceled putters.
                    self._putters.remove(putter)
                except ValueError:
                    # The putter could be removed from self._putters by a
                    # previous get_nowait call.
                    pass
                if not self.full() and not putter.cancelled():
                    # We were woken up by get_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._putters)
                raise

        return self.put_nowait(priority, *args, **kwargs)

    def put_nowait(self, priority: Any, *args: P.args, **kwargs: P.kwargs) -> "Future[V]":
        """
        Immediately adds a task with priority to the queue without waiting.

        Args:
            priority: The priority of the task.
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            The future representing the result of the task.

        Example:
            >>> fut = queue.put_nowait(priority=1, item='task')
            >>> print(await fut)
        """
        self._ensure_workers()
        fut = Future(loop=self._workers._loop)
        _Queue.put_nowait(self, (priority, args, kwargs, fut))
        return fut

    def _get(self, heappop=heappop):
        """
        Retrieves the highest priority task from the queue.

        Returns:
            The priority, task arguments, keyword arguments, and future of the task.

        Example:
            >>> task = queue._get()
            >>> print(task)
        """
        # For readability, what we're really doing is this:
        # priority, args, kwargs, fut = heappop(self._queue)
        # return args, kwargs, fut
        return heappop(self._queue)[1:]


class _VariablePriorityQueueMixin(_PriorityQueueMixin[T]):
    """
    Mixin for priority queues where task priorities can be updated dynamically.

    See Also:
        :class:`~_PriorityQueueMixin`
    """

    def _get(self, heappop=heappop):
        """
        Resorts the priority queue to consider any changes in priorities and retrieves the task with the highest updated priority.

        Args:
            heappop: Function to pop the highest priority task.

        Returns:
            The highest priority task in the queue.

        Example:
            >>> task = queue._get()
            >>> print(task)
        """
        # NOTE: Since waiter priorities can change, heappop might not return the job with the
        #       most waiters if `self._queue` is not currently in order, but we can use `heappushpop`,
        #       to ensure we get the job with the most waiters.
        return heappushpop(queue := self._queue, heappop(queue))

    def _get_key(self, *args, **kwargs) -> _SmartKey:
        """
        Generates a unique key for task identification based on arguments.

        Args:
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            The generated key for the task.

        Example:
            >>> key = queue._get_key(*args, **kwargs)
            >>> print(key)
        """
        return args, tuple(sorted(kwargs.items()))


class VariablePriorityQueue(_VariablePriorityQueueMixin[T], asyncio.PriorityQueue):
    """
    A :class:`~asyncio.PriorityQueue` subclass that allows priorities to be updated (or computed) on the fly.

    This queue supports dynamic priority updates, making it suitable for tasks
    where priorities may change over time. It ensures that tasks are processed
    based on the most current priority.

    Example:
        >>> queue = VariablePriorityQueue()
        >>> queue.put_nowait((1, 'task1'))
        >>> queue.put_nowait((2, 'task2'))
        >>> task = queue.get_nowait()
        >>> print(task)

    See Also:
        :class:`~asyncio.PriorityQueue`
    """


class SmartProcessingQueue(_VariablePriorityQueueMixin[T], ProcessingQueue[Concatenate[T, P], V]):
    """
    A processing queue that will execute jobs with the most waiters first, supporting dynamic priorities.

    This queue is designed to handle tasks with dynamic priorities, ensuring that
    tasks with the most waiters are prioritized. It is ideal for scenarios where
    task execution order is influenced by the number of waiters.

    Example:
        >>> async def process_task(data): return data.upper()
        >>> queue = SmartProcessingQueue(func=process_task, num_workers=5)
        >>> fut = await queue.put(item='task')
        >>> print(await fut)
        TASK

    See Also:
        :class:`~ProcessingQueue`
    """

    _no_futs = False
    """Whether smart futures are used."""

    _futs: "WeakValueDictionary[_SmartKey[T], SmartFuture[T]]"
    """
    Weak reference dictionary for managing smart futures.
    """

    def __init__(
        self,
        func: Callable[Concatenate[T, P], Awaitable[V]],
        num_workers: int,
        *,
        name: str = "",
        loop: Optional[AbstractEventLoop] = None,
    ) -> None:
        """
        Initializes a smart processing queue with the given worker function.

        Args:
            func: The worker function.
            num_workers: Number of worker tasks.
            name: Optional name for the queue.
            loop: Optional event loop.

        Example:
            >>> queue = SmartProcessingQueue(func=my_task_func, num_workers=3, name='smart_queue')
        """
        name = name or f"{func.__module__}.{func.__qualname__}"
        ProcessingQueue.__init__(self, func, num_workers, return_data=True, name=name, loop=loop)
        self._futs = WeakValueDictionary()

    async def put(self, *args: P.args, **kwargs: P.kwargs) -> SmartFuture[V]:
        # sourcery skip: use-contextlib-suppress
        """
        Asynchronously adds a task with smart future handling to the queue.

        Args:
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            The future representing the task's result.

        Example:
            >>> fut = await queue.put(item='task')
            >>> print(await fut)
        """
        while self.full():
            putter = self._loop.create_future()
            self._putters.append(putter)
            try:
                await putter
            except:
                putter.cancel()  # Just in case putter is not done yet.
                try:
                    # Clean self._putters from canceled putters.
                    self._putters.remove(putter)
                except ValueError:
                    # The putter could be removed from self._putters by a
                    # previous get_nowait call.
                    pass
                if not self.full() and not putter.cancelled():
                    # We were woken up by get_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._putters)
                raise
        return self.put_nowait(*args, **kwargs)

    def put_nowait(self, *args: P.args, **kwargs: P.kwargs) -> SmartFuture[V]:
        """
        Immediately adds a task with smart future handling to the queue without waiting.

        Args:
            args: Positional arguments for the task.
            kwargs: Keyword arguments for the task.

        Returns:
            The future representing the task's result.

        Example:
            >>> fut = queue.put_nowait(item='task')
            >>> print(await fut)
        """
        self._ensure_workers()
        key = self._get_key(*args, **kwargs)
        if fut := self._futs.get(key, None):
            return fut
        fut = SmartFuture(queue=self, key=key, loop=self._loop)
        self._futs[key] = fut
        Queue.put_nowait(self, (_SmartFutureRef(fut), args, kwargs))
        return fut

    def _get(self):
        """
        Retrieves the task with the highest priority from the queue.

        Returns:
            The priority, task arguments, keyword arguments, and future of the task.

        Example:
            >>> task = queue._get()
            >>> print(task)
        """
        fut, args, kwargs = _VariablePriorityQueueMixin._get(self)
        return args, kwargs, fut()

    async def _worker_coro(self) -> NoReturn:
        """
        Worker coroutine responsible for processing tasks in the queue.

        Retrieves tasks, executes them, and sets the results or exceptions for the futures.

        Raises:
            Any: Exceptions raised during task processing are logged.

        Example:
            >>> await queue._worker_coro()
        """
        get_next_job = self.get
        func = self.func
        task_done = self.task_done
        log = log_debug

        args: P.args
        kwargs: P.kwargs
        fut: SmartFuture[V]
        try:
            while True:
                try:
                    args, kwargs, fut = await get_next_job()
                except RuntimeError as e:
                    if _check_loop_is_closed(self, e):
                        return
                    raise

                if fut is None:
                    # the weakref was already cleaned up, we don't need to process this item
                    task_done()
                    continue

                log("processing %s", fut)

                try:
                    result = await func(*args, **kwargs)
                except Exception as e:
                    log("%s: %s", type(e).__name__, e)
                    try:
                        fut.set_exception(e)
                    except InvalidStateError:
                        _log_invalid_state_err("exception", func, fut, e)
                else:
                    try:
                        fut.set_result(result)
                    except InvalidStateError:
                        _log_invalid_state_err("result", func, fut, result)
                task_done()

        except Exception as e:
            logger.error("%s is broken!!!", self)
            logger.exception(e)
            raise


def _log_invalid_state_err(
    typ: Literal["result", "exception"], func: Callable, fut: Future, value: Any
) -> None:
    logger.error(
        "cannot set %s for %s %s: %s",
        typ,
        func.__name__,
        fut,
        value,
    )


def _check_loop_is_closed(queue: Queue, e: Exception) -> bool:
    if "Event loop is closed" not in str(e):
        return False
    if queue._unfinished_tasks:
        logger.error(
            "Event loop is closed. Closing %s with %s unfinished tasks",
            queue,
            queue._unfinished_tasks,
        )
    return True
