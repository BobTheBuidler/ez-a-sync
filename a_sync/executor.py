"""
This module provides several executor classes that facilitate running synchronous functions asynchronously using `asyncio`.

With these executors, you can run sync functions in your executor with `await executor.run(fn, *args, **kwargs)`.
The `executor.submit(fn, *args, **kwargs)` method works similarly to the `concurrent.futures` implementation but
returns an `asyncio.Future` instead of a `concurrent.futures.Future`.

Executor Classes:
    - :class:`AsyncProcessPoolExecutor`: A process pool executor providing asynchronous run and submit methods, with support for synchronous mode
    - :class:`AsyncThreadPoolExecutor`: A thread pool executor providing asynchronous run and submit methods, with support for synchronous mode
    - :class:`PruningThreadPoolExecutor`: An :class:`AsyncThreadPoolExecutor` that prunes inactive threads after a timeout, ensuring at least one thread remains active to prevent locks.

See Also:
    - :mod:`concurrent.futures` for the original synchronous executor implementations.
"""

import asyncio
import concurrent.futures
import multiprocessing.context
import queue
import threading
import weakref
from asyncio import sleep
from asyncio.futures import _convert_future_exc
from concurrent.futures import _base, thread

from a_sync._typing import *
from a_sync.primitives._debug import _DebugDaemonMixin


TEN_MINUTES = 60 * 10

Initializer = Callable[..., object]


class _AsyncExecutorMixin(concurrent.futures.Executor, _DebugDaemonMixin):
    """
    A mixin for Executors to provide asynchronous run and submit methods.

    This mixin allows executors to operate in both asynchronous (normal) mode and synchronous mode.
    In asynchronous (normal) mode, functions are submitted to the executor and awaited.
    In synchronous mode, functions are executed directly in the current thread.

    Examples:
        >>> async def example():
        >>>     result = await executor.run(some_function, arg1, arg2, kwarg1=value1)
        >>>     print(result)

    See Also:
        - :meth:`submit` for submitting functions to the executor.
    """

    sync_mode: bool
    """
    Indicates if the executor is in synchronous mode (max_workers == 0).

    Examples:
        >>> if executor.sync_mode:
        >>>     print("Executor is in synchronous mode.")
    """

    _max_workers: int

    _workers: str
    """The type of workers used."""

    __slots__ = "_max_workers", "_initializer", "_initargs", "_broken", "_shutdown_lock"

    async def run(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs):
        """
        A shorthand way to call `await asyncio.get_event_loop().run_in_executor(this_executor, fn, *args)`.
        Doesn't `await this_executor.run(fn, *args)` look so much better?

        In synchronous mode, the function is executed directly in the current thread.
        In asynchronous mode, the function is submitted to the executor and awaited.

        Args:
            fn: The function to run.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Examples:
            >>> async def example():
            >>>     result = await executor.run(some_function, arg1, arg2, kwarg1=value1)
            >>>     print(result)

        See Also:
            - :meth:`submit` for submitting functions to the executor.
        """
        return fn(*args, **kwargs) if self.sync_mode else await self.submit(fn, *args, **kwargs)

    @overload
    def submit(self, fn: Callable[P, T], *args: P.args, fire_and_forget: Literal[True], **kwargs: P.kwargs) -> None:  # type: ignore [override]
        """
        Submits a job to the executor without expecting a result back. The executor will execute the task silently.

        Args:
            fn: The function to submit.
            *args: Positional arguments for the function.
            fire_and_forget: True
            **kwargs: Keyword arguments for the function.

        Examples:
            >>> executor.submit(some_function, arg1, arg2, fire_and_forget=True, kwarg1=value1)

        See Also:
            - :meth:`run` for running functions with the executor.
        """

    @overload
    def submit(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[T]":  # type: ignore [override]
        """
        Submits a job to the executor and returns an :class:`asyncio.Future` that can be awaited for the result without blocking.

        Args:
            fn: The function to submit.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Examples:
            >>> future = executor.submit(some_function, arg1, arg2, kwarg1=value1)
            >>> result = await future
            >>> print(result)

        See Also:
            - :meth:`run` for running functions with the executor.
        """

    def submit(self, fn: Callable[P, T], *args: P.args, fire_and_forget: bool = False, **kwargs: P.kwargs) -> Optional["asyncio.Future[T]"]:  # type: ignore [override]
        # sourcery skip: simplify-boolean-comparison
        """
        Submits a job to the executor and returns an :class:`asyncio.Future` that can be awaited for the result without blocking.

        If `fire_and_forget` is True, the executor will not return any data and intead of a :class:`~Future` this function will return `None`.

        Args:
            fn: The function to submit.
            *args: Positional arguments for the function.
            fire_and_forget (optional): Set True to send the job to the executor without expecting a result. If `fire_and_forget` is True, this function will return None instead of a Future. Default False.
            **kwargs: Keyword arguments for the function.

        Examples:
            >>> future = executor.submit(some_function, arg1, arg2, kwarg1=value1)
            >>> result = await future
            >>> print(result)

        See Also:
            - :meth:`run` for running functions with the executor.
        """
        if fire_and_forget is True:
            # Send the job to the executor and return without creating a future or setting up callbacks
            if self.sync_mode:
                fn(*args, **kwargs)
            else:
                self.__super_submit(fn, *args, **kwargs)
            return None

        fut = self._create_future()
        if self.sync_mode:
            try:
                _set_fut_result(fut, fn(*args, **kwargs))
            except Exception as e:
                _set_fut_exception(fut, e)
        else:
            self._ensure_debug_daemon(fut, fn, *args, **kwargs)

            cf_fut = self.__super_submit(fn, *args, **kwargs)

            # TODO: implement logic to actually cancel the job, not just the future which is useless for our use case
            # def _call_check_cancel(destination: asyncio.Future):
            #     if _fut_is_cancelled(destination):
            #         cf_fut.cancel()
            #
            # fut.add_done_callback(_call_check_cancel)

            def _call_copy_future_state(cf_fut: "concurrent.futures.Future"):
                if _fut_is_cancelled(fut):
                    return
                self._call_soon_threadsafe(
                    _copy_future_state,
                    cf_fut,
                    fut,
                )

            _add_done_callback(cf_fut, _call_copy_future_state)

        return fut

    def __repr__(self) -> str:
        worker_info = f"[{self.worker_count_current}/{self._max_workers} {self._workers}]"
        identifier = getattr(self, "_thread_name_prefix", None) or hex(id(self))
        return f"<{self.__class__.__name__} {identifier} {worker_info}>"

    def __len__(self) -> int:
        # NOTE: should this be queue length instead? probably
        return self.worker_count_current

    @property
    def worker_count_current(self) -> int:
        """
        Returns the current number of workers.

        Examples:
            >>> print(f"Current worker count: {executor.worker_count_current}")
        """
        return len(getattr(self, f"_{self._workers}"))

    def __init_mixin__(self):
        self.sync_mode = self._max_workers == 0
        loop = self._get_loop()
        self._create_future = loop.create_future
        self.__super_submit = super().submit
        self._call_soon_threadsafe = loop.call_soon_threadsafe

    async def _debug_daemon(self, fut: asyncio.Future, fn, *args, **kwargs) -> None:
        """
        Runs until manually cancelled by the finished work item.

        This code will only run if `self.logger.isEnabledFor(logging.DEBUG)` is True. You do not need to include any level checks in your custom implementations.

        Args:
            fut: The future being debugged.
            fn: The function being executed.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        See Also:
            - :meth:`_start_debug_daemon` to start the debug daemon.
        """
        # TODO: make prettier strings for other types
        if type(fn).__name__ == "function":
            fnid = getattr(fn, "__qualname__", fn.__name__)
            if fn.__module__:
                fnid = f"{fn.__module__}.{fnid}"
        else:
            fnid = fn

        msg = f"%s processing %s{args}"
        if kwargs:
            msg = f"{msg[:-1]} {', '.join(f'{k}={v}' for k, v in kwargs.items())})"
        else:
            msg = f"{msg[:-2]})"

        done = fut.done
        log_debug = self.logger.debug

        while not done():
            await sleep(15)
            if not done():
                log_debug(msg, self, fnid)


# Process


class AsyncProcessPoolExecutor(_AsyncExecutorMixin, concurrent.futures.ProcessPoolExecutor):
    """
    A :class:`concurrent.futures.ProcessPoolExecutor' subclass providing asynchronous
    run and submit methods that support kwargs, with support for synchronous mode

    Examples:
        >>> executor = AsyncProcessPoolExecutor(max_workers=4)
        >>> future = executor.submit(some_function, arg1, arg2, kwarg1='kwarg1')
        >>> result = await future
    """

    _workers = "processes"
    """The type of workers used, set to "processes"."""

    __slots__ = (
        "_mp_context",
        "_processes",
        "_pending_work_items",
        "_call_queue",
        "_result_queue",
        "_queue_management_thread",
        "_queue_count",
        "_shutdown_thread",
        "_work_ids",
        "_queue_management_thread_wakeup",
    )

    def __init__(
        self,
        max_workers: Optional[int] = None,
        mp_context: Optional[multiprocessing.context.BaseContext] = None,
        initializer: Optional[Initializer] = None,
        initargs: Tuple[Any, ...] = (),
    ) -> None:
        """
        Initializes the AsyncProcessPoolExecutor.

        Args:
            max_workers: The maximum number of workers. Defaults to None.
            mp_context: The multiprocessing context. Defaults to None.
            initializer: An initializer callable. Defaults to None.
            initargs: Arguments for the initializer. Defaults to ().

        Examples:
            >>> executor = AsyncProcessPoolExecutor(max_workers=4)
            >>> future = executor.submit(some_function, arg1, arg2)
            >>> result = await future
        """
        if max_workers == 0:
            concurrent.futures.ProcessPoolExecutor.__init__(
                self, 1, mp_context, initializer, initargs
            )
            self._max_workers = 0
        else:
            concurrent.futures.ProcessPoolExecutor.__init__(
                self, max_workers, mp_context, initializer, initargs
            )
        self.__init_mixin__()


# Thread


class AsyncThreadPoolExecutor(_AsyncExecutorMixin, concurrent.futures.ThreadPoolExecutor):
    """
    A :class:`concurrent.futures.ThreadPoolExecutor' subclass providing asynchronous
    run and submit methods that support kwargs, with support for synchronous mode

    Examples:
        >>> executor = AsyncThreadPoolExecutor(max_workers=10, thread_name_prefix="MyThread")
        >>> future = executor.submit(some_function, arg1, arg2, kwarg1='kwarg1')
        >>> result = await future
    """

    _workers = "threads"
    """The type of workers used, set to "threads"."""

    __slots__ = (
        "_work_queue",
        "_idle_semaphore",
        "_threads",
        "_shutdown",
        "_thread_name_prefix",
    )

    def __init__(
        self,
        max_workers: Optional[int] = None,
        thread_name_prefix: str = "",
        initializer: Optional[Initializer] = None,
        initargs: Tuple[Any, ...] = (),
    ) -> None:
        """
        Initializes the AsyncThreadPoolExecutor.

        Args:
            max_workers: The maximum number of workers. Defaults to None.
            thread_name_prefix: Prefix for thread names. Defaults to ''.
            initializer: An initializer callable. Defaults to None.
            initargs: Arguments for the initializer. Defaults to ().

        Examples:
            >>> executor = AsyncThreadPoolExecutor(max_workers=10, thread_name_prefix="MyThread")
            >>> future = executor.submit(some_function, arg1, arg2)
            >>> result = await future
        """
        if max_workers == 0:
            concurrent.futures.ThreadPoolExecutor.__init__(
                self, 1, thread_name_prefix, initializer, initargs
            )
            self._max_workers = 0
        else:
            concurrent.futures.ThreadPoolExecutor.__init__(
                self, max_workers, thread_name_prefix, initializer, initargs
            )
        self.__init_mixin__()


AsyncExecutor = Union[AsyncThreadPoolExecutor, AsyncProcessPoolExecutor]

# For backward-compatibility
ThreadPoolExecutor = AsyncThreadPoolExecutor
ProcessPoolExecutor = AsyncProcessPoolExecutor

# Pruning thread pool


def _worker(executor_reference, work_queue, initializer, initargs, timeout):  # NOTE: NEW 'timeout'
    """
    Worker function for the PruningThreadPoolExecutor.

    Args:
        executor_reference: A weak reference to the executor.
        work_queue: The work queue.
        initializer: The initializer function.
        initargs: Arguments for the initializer.
        timeout: Timeout duration for pruning inactive threads.

    See Also:
        - :class:`PruningThreadPoolExecutor` for more details on thread pruning.
    """
    if initializer is not None:
        try:
            initializer(*initargs)
        except BaseException:
            _base.LOGGER.critical("Exception in initializer:", exc_info=True)
            executor = executor_reference()
            if executor is not None:
                executor._initializer_failed()
            return

    try:
        while True:
            try:  # NOTE: NEW
                work_item = work_queue.get(block=True, timeout=timeout)  # NOTE: NEW
            except queue.Empty:  # NOTE: NEW
                # Its been 'timeout' seconds and there are no new work items.  # NOTE: NEW
                # Let's suicide the thread.  # NOTE: NEW
                executor = executor_reference()  # NOTE: NEW

                with executor._adjusting_lock:  # NOTE: NEW
                    # NOTE: We keep a minimum of one thread active to prevent locks
                    if len(executor) > 1:  # NOTE: NEW
                        t = threading.current_thread()  # NOTE: NEW
                        executor._threads.remove(t)  # NOTE: NEW
                        thread._threads_queues.pop(t)  # NOTE: NEW
                        # Let the executor know we have one less idle thread available
                        executor._idle_semaphore.acquire(blocking=False)  # NOTE: NEW
                        return  # NOTE: NEW
                continue

            if work_item is not None:
                work_item.run()
                # Delete references to object. See issue16284
                del work_item

                # attempt to increment idle count
                executor = executor_reference()
                if executor is not None:
                    executor._idle_semaphore.release()
                del executor
                continue

            executor = executor_reference()
            # Exit if:
            #   - The interpreter is shutting down OR
            #   - The executor that owns the worker has been collected OR
            #   - The executor that owns the worker has been shutdown OR
            if thread._shutdown or executor is None or executor._shutdown:
                # Flag the executor as shutting down as early as possible if it is not gc-ed yet.
                if executor is not None:
                    executor._shutdown = True
                # Notice other workers
                work_queue.put(None)
                return
            del executor
    except BaseException:
        _base.LOGGER.critical("Exception in worker", exc_info=True)


class PruningThreadPoolExecutor(AsyncThreadPoolExecutor):
    """
    This :class:`~AsyncThreadPoolExecutor` implementation prunes inactive threads after 'timeout' seconds without a work item.
    Pruned threads will be automatically recreated as needed for future workloads. Up to 'max_threads' can be active at any one time.
    The executor ensures that at least one active thread remains to prevent locks.

    Note:
        The `_worker` function includes a check (`len(executor) > 1`) to ensure that at least one thread remains active.
        This prevents the executor from having zero active threads, which could lead to deadlocks.

    Examples:
        >>> executor = PruningThreadPoolExecutor(max_workers=5, timeout=300)
        >>> future = executor.submit(some_function, arg1, arg2, kwarg1='kwarg1')
        >>> result = await future
    """

    __slots__ = "_timeout", "_adjusting_lock"

    def __init__(
        self,
        max_workers=None,
        thread_name_prefix="",
        initializer=None,
        initargs=(),
        timeout=TEN_MINUTES,
    ):
        """
        Initializes the PruningThreadPoolExecutor.

        Args:
            max_workers: The maximum number of workers. Defaults to None.
            thread_name_prefix: Prefix for thread names. Defaults to ''.
            initializer: An initializer callable. Defaults to None.
            initargs: Arguments for the initializer. Defaults to ().
            timeout: Timeout duration for pruning inactive threads. Defaults to TEN_MINUTES.

        Examples:
            >>> executor = PruningThreadPoolExecutor(max_workers=5, timeout=300)
            >>> future = executor.submit(some_function, arg1, arg2)
            >>> result = await future
        """

        self._timeout = timeout
        """Timeout duration for pruning inactive threads."""

        self._adjusting_lock = threading.Lock()
        """Lock used to adjust the number of threads."""

        AsyncThreadPoolExecutor.__init__(
            self, max_workers, thread_name_prefix, initializer, initargs
        )

    def __len__(self) -> int:
        return len(self._threads)

    def _adjust_thread_count(self):
        """
        Adjusts the number of threads based on workload and idle threads.

        See Also:
            - :func:`_worker` for the worker function that handles thread pruning.
        """
        with self._adjusting_lock:
            # if idle threads are available, don't spin new threads
            if self._idle_semaphore.acquire(timeout=0):
                return

            # When the executor gets lost, the weakref callback will wake up
            # the worker threads.
            def weakref_cb(_, q=self._work_queue):
                q.put(None)

            num_threads = len(self._threads)
            if num_threads < self._max_workers:
                thread_name = "%s_%d" % (self._thread_name_prefix or self, num_threads)
                t = threading.Thread(
                    name=thread_name,
                    target=_worker,
                    args=(
                        weakref.ref(self, weakref_cb),
                        self._work_queue,
                        self._initializer,
                        self._initargs,
                        self._timeout,
                    ),
                )
                t.daemon = True
                t.start()
                self._threads.add(t)
                thread._threads_queues[t] = self._work_queue


def _copy_future_state(cf_fut: concurrent.futures.Future, fut: asyncio.Future):
    """Internal helper to copy state from another Future.

    The other Future may be a concurrent.futures.Future.
    """
    # check this again in case it was cancelled since the last check
    if _fut_is_cancelled(fut):
        return
    exception = _get_cf_fut_exception(cf_fut)
    if exception is None:
        _set_fut_result(fut, _get_cf_fut_result(cf_fut))
    else:
        _set_fut_exception(fut, _convert_future_exc(exception))


_fut_is_cancelled = asyncio.Future.cancelled
_get_cf_fut_result = concurrent.futures.Future.result
_get_cf_fut_exception = concurrent.futures.Future.exception
_set_fut_result = asyncio.Future.set_result
_set_fut_exception = asyncio.Future.set_exception
_add_done_callback = concurrent.futures.Future.add_done_callback


executor = PruningThreadPoolExecutor(128)

__all__ = [
    "AsyncThreadPoolExecutor",
    "AsyncProcessPoolExecutor",
    "PruningThreadPoolExecutor",
]
