import pytest
import weakref
from asyncio import CancelledError, create_task, get_event_loop, sleep

from a_sync._smart import (
    SmartFuture,
    SmartTask,
    WeakSet,
    set_smart_task_factory,
    shield,
    smart_task_factory,
)


@pytest.mark.asyncio_cooperative
async def test_smart_future_init_no_args():
    fut = SmartFuture()
    assert fut._loop is get_event_loop()
    assert fut._queue is None
    assert fut._key is None
    assert isinstance(fut._waiters, WeakSet)
    assert len(fut._waiters) == 0


@pytest.mark.asyncio_cooperative
async def test_smart_future_init_loop_arg():
    loop = get_event_loop()
    fut = SmartFuture(loop=loop)
    assert fut._loop is loop
    assert fut._queue is None
    assert fut._key is None
    assert isinstance(fut._waiters, WeakSet)
    assert len(fut._waiters) == 0


@pytest.mark.asyncio_cooperative
async def test_smart_future_await():
    fut = SmartFuture()
    get_event_loop().call_soon(fut.set_result, None)
    await fut


@pytest.mark.asyncio_cooperative
async def test_smart_future_await_exc():
    fut = SmartFuture()
    get_event_loop().call_soon(fut.set_exception, ValueError("test"))
    with pytest.raises(ValueError, match="test"):
        await fut


@pytest.mark.asyncio_cooperative
async def test_smart_future_await_cancelled():
    fut = SmartFuture()
    get_event_loop().call_soon(fut.cancel)
    with pytest.raises(CancelledError):
        await fut


@pytest.mark.asyncio_cooperative
async def test_smart_task_await():
    await SmartTask(sleep(0.1), loop=None)


@pytest.mark.asyncio_cooperative
async def test_smart_task_await_exc():
    async def raise_exc():
        raise ValueError("test")

    with pytest.raises(ValueError, match="test"):
        await SmartTask(raise_exc(), loop=None)


@pytest.mark.asyncio_cooperative
async def test_smart_task_await_cancelled():
    task = SmartTask(sleep(0.1), loop=None)
    get_event_loop().call_soon(task.cancel)
    with pytest.raises(CancelledError):
        await task


@pytest.mark.asyncio_cooperative
async def test_smart_task_name():
    t = SmartTask(sleep(0.1), loop=None, name="test")
    assert t.get_name() == "test"


async def smart_task_coro():
    task = create_task(sleep(0.1))
    assert isinstance(task, SmartTask)
    assert await task is None


def test_set_smart_task_factory():
    set_smart_task_factory()
    loop = get_event_loop()
    assert loop.get_task_factory() is smart_task_factory
    loop.run_until_complete(smart_task_coro())


def test_set_smart_task_factory_with_loop():
    loop = get_event_loop()
    set_smart_task_factory(loop)
    assert loop.get_task_factory() is smart_task_factory
    loop.run_until_complete(smart_task_coro())


@pytest.mark.asyncio_cooperative
async def test_shield():
    task = create_task(sleep(1))
    shielded = shield(task)
    await shielded


@pytest.mark.asyncio_cooperative
async def test_shield_exc():
    async def raise_exc():
        raise ValueError("test")

    task = create_task(raise_exc())
    shielded = shield(task)
    with pytest.raises(ValueError, match="test"):
        await shielded


@pytest.mark.asyncio_cooperative
async def test_shield_cancel_inner():
    task = create_task(sleep(1))
    shielded = shield(task)
    task.cancel()
    with pytest.raises(CancelledError):
        await task
    with pytest.raises(CancelledError):
        await shielded


@pytest.mark.asyncio_cooperative
async def test_shield_cancel_outer():
    task = create_task(sleep(1))
    shielded = shield(task)
    shielded.cancel()
    await sleep(0)
    assert not task.cancelled()
    await task
    with pytest.raises(CancelledError):
        await shielded
