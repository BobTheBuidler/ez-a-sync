from a_sync._typing import *
import asyncio
import concurrent.futures
import multiprocessing.context
from _typeshed import Incomplete
from a_sync.primitives._debug import _DebugDaemonMixin
from functools import cached_property
from typing import Any

__all__ = [
    "AsyncThreadPoolExecutor",
    "AsyncProcessPoolExecutor",
    "PruningThreadPoolExecutor",
]

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

    def submit(
        self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> asyncio.Future[T]:
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

    def __len__(self) -> int: ...
    @cached_property
    def sync_mode(self) -> bool:
        """
        Indicates if the executor is in synchronous mode (max_workers == 0).

        Examples:
            >>> if executor.sync_mode:
            >>>     print("Executor is in synchronous mode.")
        """

    @property
    def worker_count_current(self) -> int:
        """
        Returns the current number of workers.

        Examples:
            >>> print(f"Current worker count: {executor.worker_count_current}")
        """

class AsyncProcessPoolExecutor(
    _AsyncExecutorMixin, concurrent.futures.ProcessPoolExecutor
):
    """
    A :class:`concurrent.futures.ProcessPoolExecutor' subclass providing asynchronous run and submit methods that support kwargs,
    with support for synchronous mode

    Examples:
        >>> executor = AsyncProcessPoolExecutor(max_workers=4)
        >>> future = executor.submit(some_function, arg1, arg2, kwarg1='kwarg1')
        >>> result = await future
    """

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

class AsyncThreadPoolExecutor(
    _AsyncExecutorMixin, concurrent.futures.ThreadPoolExecutor
):
    """
    A :class:`concurrent.futures.ThreadPoolExecutor\' subclass providing asynchronous run and submit methods that support kwargs,
    with support for synchronous mode

    Examples:
        >>> executor = AsyncThreadPoolExecutor(max_workers=10, thread_name_prefix="MyThread")
        >>> future = executor.submit(some_function, arg1, arg2, kwarg1=\'kwarg1\')
        >>> result = await future
    """

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
            thread_name_prefix: Prefix for thread names. Defaults to \'\'.
            initializer: An initializer callable. Defaults to None.
            initargs: Arguments for the initializer. Defaults to ().

        Examples:
            >>> executor = AsyncThreadPoolExecutor(max_workers=10, thread_name_prefix="MyThread")
            >>> future = executor.submit(some_function, arg1, arg2)
            >>> result = await future
        """

ProcessPoolExecutor = AsyncProcessPoolExecutor
ThreadPoolExecutor = AsyncThreadPoolExecutor

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

    def __init__(
        self,
        max_workers: Incomplete | None = None,
        thread_name_prefix: str = "",
        initializer: Incomplete | None = None,
        initargs=(),
        timeout=...,
    ) -> None:
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

    def __len__(self) -> int: ...
