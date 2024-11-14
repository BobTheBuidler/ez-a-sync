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
import functools
import heapq
import logging
import sys
import weakref

from a_sync import _smart
from a_sync.asyncio.create_task import create_task
from a_sync._typing import *

logger = logging.getLogger(__name__)

if sys.version_info < (3, 9):

    class _Queue(asyncio.Queue, Generic[T]):
        __slots__ = (
            "_maxsize",
            "_loop",
            "_getters",
            "_putters",
            "_unfinished_tasks",
            "_finished",
        )

else:

    class _Queue(asyncio.Queue[T]):
        __slots__ = "_maxsize", "_getters", "_putters", "_unfinished_tasks", "_finished"


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

    async def get(self) -> T:
        self._queue
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
        return _Queue.put(self, item)

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
        except asyncio.QueueEmpty:
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
        values: List[T] = []
        while True:
            try:
                values.append(self.get_nowait())
            except asyncio.QueueEmpty as e:
                if not values:
                    raise asyncio.QueueEmpty from e
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
        items = []
        while len(items) < i and not can_return_less:
            try:
                items.extend(
                    self.get_multi_nowait(i - len(items), can_return_less=True)
                )
            except asyncio.QueueEmpty:
                items = [await self.get()]
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
        items = []
        for _ in range(i):
            try:
                items.append(self.get_nowait())
            except asyncio.QueueEmpty:
                if items and can_return_less:
                    return items
                # put these back in the queue since we didn't return them
                for value in items:
                    self.put_nowait(value)
                raise asyncio.QueueEmpty from None
        return items


class ProcessingQueue(_Queue[Tuple[P, "asyncio.Future[V]"]], Generic[P, V]):
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

    __slots__ = "func", "num_workers", "_worker_coro"

    def __init__(
        self,
        func: Callable[P, Awaitable[V]],
        num_workers: int,
        *,
        return_data: bool = True,
        name: str = "",
        loop: Optional[asyncio.AbstractEventLoop] = None,
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
        if sys.version_info < (3, 10):
            super().__init__(loop=loop)
        elif loop:
            raise NotImplementedError(
                f"You cannot pass a value for `loop` in python {sys.version_info}"
            )
        else:
            super().__init__()

        self.func = func
        """The function that each worker will process."""

        self.num_workers = num_workers
        """The number of worker tasks for processing."""

        self._name = name
        """Optional name for the queue."""

        self._no_futs = not return_data
        """Indicates whether tasks will return data via futures."""

        @functools.wraps(func)
        async def _worker_coro() -> NoReturn:
            """Worker coroutine for processing tasks."""
            return await self.__worker_coro()

        self._worker_coro = _worker_coro

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

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[V]":
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
            asyncio.get_event_loop().call_exception_handler(context)

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

    async def put(self, *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[V]":
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
        self._ensure_workers()
        if self._no_futs:
            return await super().put((args, kwargs))
        fut = self._create_future()
        await super().put((args, kwargs, fut))
        return fut

    def put_nowait(self, *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[V]":
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
            return super().put_nowait((args, kwargs))
        fut = self._create_future()
        super().put_nowait((args, kwargs, weakref.proxy(fut)))
        return fut

    def _create_future(self) -> "asyncio.Future[V]":
        """Creates a future for the task."""
        return asyncio.get_event_loop().create_future()

    def _ensure_workers(self) -> None:
        """Ensures that the worker tasks are running."""
        if self._closed:
            raise RuntimeError(f"{type(self).__name__} is closed: ", self) from None
        if self._workers.done():
            worker_subtasks: List["asyncio.Task[NoReturn]"] = self._workers._workers
            for worker in worker_subtasks:
                if worker.done():  # its only done if its broken
                    exc = worker.exception()
                    # re-raise with clean traceback
                    try:
                        raise type(exc)(*exc.args).with_traceback(exc.__traceback__)  # type: ignore [union-attr]
                    except TypeError as e:
                        raise exc.with_traceback(exc.__traceback__) from e
            # this should never be reached, but just in case
            exc = self._workers.exception()
            try:
                # re-raise with clean traceback
                raise type(exc)(*exc.args).with_traceback(exc.__traceback__)  # type: ignore [union-attr]
            except TypeError as e:
                raise exc.with_traceback(exc.__traceback__) from e

    @functools.cached_property
    def _workers(self) -> "asyncio.Task[NoReturn]":
        """Creates and manages the worker tasks for the queue."""
        logger.debug("starting worker task for %s", self)
        workers = [
            create_task(
                coro=self._worker_coro(),
                name=f"{self.name} [Task-{i}]",
                log_destroy_pending=False,
            )
            for i in range(self.num_workers)
        ]
        task = create_task(
            asyncio.gather(*workers),
            name=f"{self.name} worker main Task",
            log_destroy_pending=False,
        )
        task._workers = workers
        return task

    async def __worker_coro(self) -> NoReturn:
        """
        The coroutine executed by worker tasks to process the queue.
        """
        args: P.args
        kwargs: P.kwargs
        if self._no_futs:
            while True:
                try:
                    args, kwargs = await self.get()
                    await self.func(*args, **kwargs)
                except Exception as e:
                    logger.error("%s in worker for %s!", type(e).__name__, self)
                    logger.exception(e)
                self.task_done()
        else:
            fut: asyncio.Future[V]
            while True:
                try:
                    args, kwargs, fut = await self.get()
                    try:
                        if fut is None:
                            # the weakref was already cleaned up, we don't need to process this item
                            self.task_done()
                            continue
                        result = await self.func(*args, **kwargs)
                        fut.set_result(result)
                    except asyncio.exceptions.InvalidStateError:
                        logger.error(
                            "cannot set result for %s %s: %s",
                            self.func.__name__,
                            fut,
                            result,
                        )
                    except Exception as e:
                        try:
                            fut.set_exception(e)
                        except asyncio.exceptions.InvalidStateError:
                            logger.error(
                                "cannot set exception for %s %s: %s",
                                self.func.__name__,
                                fut,
                                e,
                            )
                    self.task_done()
                except Exception as e:
                    logger.error(
                        "%s for %s is broken!!!", type(self).__name__, self.func
                    )
                    logger.exception(e)
                    raise


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
        raise TypeError(
            f"`can_return_less` must be boolean. You passed {can_return_less}"
        )
    if i <= 1:
        raise ValueError(f"`i` must be an integer greater than 1. You passed {i}")


class _SmartFutureRef(weakref.ref, Generic[T]):
    """
    Weak reference for :class:`~_smart.SmartFuture` objects used in priority queues.

    See Also:
        :class:`~_smart.SmartFuture`
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
        return False if strong_other is None else strong_self < strong_other


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

    def _put(self, item, heappush=heapq.heappush):
        """
        Adds an item to the priority queue based on its priority.

        Example:
            >>> queue._put(item='task')
        """
        heappush(self._queue, item)

    def _get(self, heappop=heapq.heappop):
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

    async def put(
        self, priority: Any, *args: P.args, **kwargs: P.kwargs
    ) -> "asyncio.Future[V]":
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
        self._ensure_workers()
        fut = asyncio.get_event_loop().create_future()
        await super().put(self, (priority, args, kwargs, fut))
        return fut

    def put_nowait(
        self, priority: Any, *args: P.args, **kwargs: P.kwargs
    ) -> "asyncio.Future[V]":
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
        fut = self._create_future()
        super().put_nowait(self, (priority, args, kwargs, fut))
        return fut

    def _get(self, heappop=heapq.heappop):
        """
        Retrieves the highest priority task from the queue.

        Returns:
            The priority, task arguments, keyword arguments, and future of the task.

        Example:
            >>> task = queue._get()
            >>> print(task)
        """
        priority, args, kwargs, fut = heappop(self._queue)
        return args, kwargs, fut


class _VariablePriorityQueueMixin(_PriorityQueueMixin[T]):
    """
    Mixin for priority queues where task priorities can be updated dynamically.

    See Also:
        :class:`~_PriorityQueueMixin`
    """

    def _get(self, heapify=heapq.heapify, heappop=heapq.heappop):
        """
        Resorts the priority queue to consider any changes in priorities and retrieves the task with the highest updated priority.

        Args:
            heapify: Function to resort the heap.
            heappop: Function to pop the highest priority task.

        Returns:
            The highest priority task in the queue.

        Example:
            >>> task = queue._get()
            >>> print(task)
        """
        heapify(self._queue)
        # take the job with the most waiters
        return heappop(self._queue)

    def _get_key(self, *args, **kwargs) -> _smart._Key:
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
        return (args, tuple((kwarg, kwargs[kwarg]) for kwarg in sorted(kwargs)))


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


class SmartProcessingQueue(
    _VariablePriorityQueueMixin[T], ProcessingQueue[Concatenate[T, P], V]
):
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

    _futs: "weakref.WeakValueDictionary[_smart._Key[T], _smart.SmartFuture[T]]"
    """
    Weak reference dictionary for managing smart futures.
    """

    def __init__(
        self,
        func: Callable[Concatenate[T, P], Awaitable[V]],
        num_workers: int,
        *,
        name: str = "",
        loop: Optional[asyncio.AbstractEventLoop] = None,
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
        super().__init__(func, num_workers, return_data=True, name=name, loop=loop)
        self._futs = weakref.WeakValueDictionary()

    async def put(self, *args: P.args, **kwargs: P.kwargs) -> _smart.SmartFuture[V]:
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
        self._ensure_workers()
        key = self._get_key(*args, **kwargs)
        if fut := self._futs.get(key, None):
            return fut
        fut = self._create_future(key)
        self._futs[key] = fut
        await Queue.put(self, (_SmartFutureRef(fut), args, kwargs))
        return fut

    def put_nowait(self, *args: P.args, **kwargs: P.kwargs) -> _smart.SmartFuture[V]:
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
        fut = self._create_future(key)
        self._futs[key] = fut
        Queue.put_nowait(self, (_SmartFutureRef(fut), args, kwargs))
        return fut

    def _create_future(self, key: _smart._Key) -> "asyncio.Future[V]":
        """Creates a smart future for the task."""
        return _smart.create_future(queue=self, key=key, loop=self._loop)

    def _get(self):
        """
        Retrieves the task with the highest priority from the queue.

        Returns:
            The priority, task arguments, keyword arguments, and future of the task.

        Example:
            >>> task = queue._get()
            >>> print(task)
        """
        fut, args, kwargs = super()._get()
        return args, kwargs, fut()

    async def __worker_coro(self) -> NoReturn:
        """
        Worker coroutine responsible for processing tasks in the queue.

        Retrieves tasks, executes them, and sets the results or exceptions for the futures.

        Raises:
            Any: Exceptions raised during task processing are logged.

        Example:
            >>> await queue.__worker_coro()
        """
        args: P.args
        kwargs: P.kwargs
        fut: _smart.SmartFuture[V]
        while True:
            try:
                try:
                    args, kwargs, fut = await self.get()
                    if fut is None:
                        # the weakref was already cleaned up, we don't need to process this item
                        self.task_done()
                        continue
                    logger.debug("processing %s", fut)
                    result = await self.func(*args, **kwargs)
                    fut.set_result(result)
                except asyncio.exceptions.InvalidStateError:
                    logger.error(
                        "cannot set result for %s %s: %s",
                        self.func.__name__,
                        fut,
                        result,
                    )
                except Exception as e:
                    logger.debug("%s: %s", type(e).__name__, e)
                    try:
                        fut.set_exception(e)
                    except asyncio.exceptions.InvalidStateError:
                        logger.error(
                            "cannot set exception for %s %s: %s",
                            self.func.__name__,
                            fut,
                            e,
                        )
                self.task_done()
            except Exception as e:
                logger.error("%s for %s is broken!!!", type(self).__name__, self.func)
                logger.exception(e)
                raise
