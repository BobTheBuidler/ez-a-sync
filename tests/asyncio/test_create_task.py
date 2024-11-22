import logging
import pytest
import asyncio
from a_sync.asyncio.create_task import create_task


@pytest.mark.asyncio_cooperative
async def test_create_task_with_coroutine():
    async def sample_coroutine():
        return "Hello, World!"

    task = create_task(sample_coroutine())
    result = await task
    assert result == "Hello, World!"


@pytest.mark.asyncio_cooperative
async def test_create_task_with_future():
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    future.set_result("Future Result")

    task = create_task(future)
    result = await task
    assert result == "Future Result"


@pytest.mark.asyncio_cooperative
async def test_create_task_with_name():
    async def sample_coroutine():
        return "Named Task"

    task = create_task(sample_coroutine(), name="TestTask")
    assert task.get_name() == "TestTask"


@pytest.mark.asyncio_cooperative
async def test_create_task_skip_gc_until_done():
    async def sample_coroutine():
        return "GC Test"

    task = create_task(sample_coroutine(), skip_gc_until_done=True)
    result = await task
    assert result == "GC Test"


@pytest.mark.asyncio_cooperative
async def test_create_task_log_destroy_pending():
    async def sample_coroutine():
        return "Log Test"

    task = create_task(sample_coroutine(), log_destroy_pending=False)
    assert not task._log_destroy_pending


@pytest.mark.asyncio_cooperative
async def test_create_task_handles_non_coroutine_awaitable():
    class CustomAwaitable:
        def __await__(self):
            yield
            return "Custom Awaitable Result"

    result = await create_task(CustomAwaitable())
    assert result == "Custom Awaitable Result"
