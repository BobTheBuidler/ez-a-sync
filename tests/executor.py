import asyncio
import time

import pytest

from a_sync import ProcessPoolExecutor, ThreadPoolExecutor, PruningThreadPoolExecutor


@pytest.mark.asyncio
async def test_process_pool_executor_run():
    """Tests the ProcessPoolExecutor by running and submitting the work function asynchronously."""
    executor = ProcessPoolExecutor(1)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_thread_pool_executor_run():
    """Tests the ThreadPoolExecutor by running and submitting the work function asynchronously."""
    executor = ThreadPoolExecutor(1)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_pruning_thread_pool_executor_run():
    """Tests the PruningThreadPoolExecutor by running and submitting the work function asynchronously."""
    executor = PruningThreadPoolExecutor(1)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_process_pool_executor_submit():
    """Tests the ProcessPoolExecutor by submitting the work function asynchronously."""
    executor = ProcessPoolExecutor(1)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_thread_pool_executor_submit():
    """Tests the ThreadPoolExecutor by submitting the work function asynchronously."""
    executor = ThreadPoolExecutor(1)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_pruning_thread_pool_executor_submit():
    """Tests the PruningThreadPoolExecutor by submitting the work function asynchronously."""
    executor = PruningThreadPoolExecutor(1)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_process_pool_executor_sync_run():
    """Tests the ProcessPoolExecutor by running and submitting the work function synchronously."""
    executor = ProcessPoolExecutor(0)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_thread_pool_executor_sync_run():
    """Tests the ThreadPoolExecutor by running and submitting the work function synchronously."""
    executor = ThreadPoolExecutor(0)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_pruning_thread_pool_executor_sync_run():
    """Tests the PruningThreadPoolExecutor by running and submitting the work function synchronously."""
    executor = PruningThreadPoolExecutor(0)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio
async def test_process_pool_executor_sync_submit():
    """Tests the ProcessPoolExecutor by submitting the work function synchronously."""
    executor = ProcessPoolExecutor(0)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_thread_pool_executor_sync_submit():
    """Tests the ThreadPoolExecutor by submitting the work function synchronously."""
    executor = ThreadPoolExecutor(0)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio
async def test_pruning_thread_pool_executor_sync_submit():
    """Tests the PruningThreadPoolExecutor by submitting the work function synchronously."""
    executor = PruningThreadPoolExecutor(0)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut
