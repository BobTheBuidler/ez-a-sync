import asyncio
import pytest

from a_sync._smart import SmartTask


@pytest.mark.asyncio_cooperative
async def test_smart_task_await():
    await SmartTask(asyncio.sleep(0.1), loop=None)


@pytest.mark.asyncio_cooperative
async def test_smart_task_name():
    t = SmartTask(asyncio.sleep(0.1), loop=None, name="test")
    assert t.get_name() == "test"
