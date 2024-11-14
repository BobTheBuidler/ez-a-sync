import asyncio
import time

import pytest

from a_sync import ProcessPoolExecutor, ThreadPoolExecutor, PruningThreadPoolExecutor


@pytest.mark.asyncio
async def test_process_pool_executor_run():
    """Test the :class:`ProcessPoolExecutor` by running and submitting the work function asynchronously.

    This test ensures that the :meth:`~ProcessPoolExecutor.run` method of the
    :class:`~ProcessPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~ProcessPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = ProcessPoolExecutor(1)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_thread_pool_executor_run():
    """Test the :class:`ThreadPoolExecutor` by running and submitting the work function asynchronously.

    This test ensures that the :meth:`~ThreadPoolExecutor.run` method of the
    :class:`~ThreadPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~ThreadPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = ThreadPoolExecutor(1)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_pruning_thread_pool_executor_run():
    """Test the :class:`PruningThreadPoolExecutor` by running and submitting the work function asynchronously.

    This test ensures that the :meth:`~PruningThreadPoolExecutor.run` method of the
    :class:`~PruningThreadPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~PruningThreadPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = PruningThreadPoolExecutor(1)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_process_pool_executor_submit():
    """Test the :class:`ProcessPoolExecutor` by submitting the work function.

    This test ensures that the :meth:`~ProcessPoolExecutor.submit` method of the
    :class:`~ProcessPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~ProcessPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~ProcessPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = ProcessPoolExecutor(1)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_thread_pool_executor_submit():
    """Test the :class:`ThreadPoolExecutor` by submitting the work function.

    This test ensures that the :meth:`~ThreadPoolExecutor.submit` method of the
    :class:`~ThreadPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~ThreadPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~ThreadPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = ThreadPoolExecutor(1)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_pruning_thread_pool_executor_submit():
    """Test the :class:`PruningThreadPoolExecutor` by submitting the work function.

    This test ensures that the :meth:`~PruningThreadPoolExecutor.submit` method of the
    :class:`~PruningThreadPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~PruningThreadPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~PruningThreadPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = PruningThreadPoolExecutor(1)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_process_pool_executor_sync_run():
    """Test the :class:`ProcessPoolExecutor` by running and submitting the work function synchronously.

    This test ensures that the :meth:`~ProcessPoolExecutor.run` method of the
    :class:`~ProcessPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~ProcessPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = ProcessPoolExecutor(0)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_thread_pool_executor_sync_run():
    """Test the :class:`ThreadPoolExecutor` by running and submitting the work function synchronously.

    This test ensures that the :meth:`~ThreadPoolExecutor.run` method of the
    :class:`~ThreadPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~ThreadPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = ThreadPoolExecutor(0)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_pruning_thread_pool_executor_sync_run():
    """Test the :class:`PruningThreadPoolExecutor` by running and submitting the work function synchronously.

    This test ensures that the :meth:`~PruningThreadPoolExecutor.run` method of the
    :class:`~PruningThreadPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~PruningThreadPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = PruningThreadPoolExecutor(0)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_process_pool_executor_sync_submit():
    """Test the :class:`ProcessPoolExecutor` by submitting the work function synchronously.

    This test ensures that the :meth:`~ProcessPoolExecutor.submit` method of the
    :class:`~ProcessPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~ProcessPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~ProcessPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = ProcessPoolExecutor(0)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_thread_pool_executor_sync_submit():
    """Test the :class:`ThreadPoolExecutor` by submitting the work function synchronously.

    This test ensures that the :meth:`~ThreadPoolExecutor.submit` method of the
    :class:`~ThreadPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~ThreadPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~ThreadPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = ThreadPoolExecutor(0)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_pruning_thread_pool_executor_sync_submit():
    """Test the :class:`PruningThreadPoolExecutor` by submitting the work function synchronously.

    This test ensures that the :meth:`~PruningThreadPoolExecutor.submit` method of the
    :class:`~PruningThreadPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~PruningThreadPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~PruningThreadPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = PruningThreadPoolExecutor(0)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut
