import pytest
from asyncio import create_task, get_event_loop, sleep

from a_sync._smart import SmartTask, set_smart_task_factory, smart_task_factory


@pytest.mark.asyncio_cooperative
async def test_smart_task_await():
    await SmartTask(sleep(0.1), loop=None)


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
