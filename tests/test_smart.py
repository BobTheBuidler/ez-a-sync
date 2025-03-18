import pytest
from asyncio import create_task, get_event_loop, sleep

from a_sync._smart import SmartTask, set_smart_task_factory


@pytest.mark.asyncio_cooperative
async def test_smart_task_await():
    await SmartTask(sleep(0.1), loop=None)


@pytest.mark.asyncio_cooperative
async def test_smart_task_name():
    t = SmartTask(sleep(0.1), loop=None, name="test")
    assert t.get_name() == "test"


def test_set_smart_task_factory():
    set_smart_task_factory()
    loop = get_event_loop()

    async def do_stuff():
        task = create_task(sleep(0))
        assert isinstance(task, SmartTask)

    loop.run_until_complete(do_stuff())


def test_set_smart_task_factory_with_loop():
    loop = get_event_loop()
    set_smart_task_factory(loop)

    async def do_stuff():
        task = create_task(sleep(0))
        assert isinstance(task, SmartTask)

    loop.run_until_complete(do_stuff())
