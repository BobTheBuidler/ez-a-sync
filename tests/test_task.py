import asyncio
import pytest

from a_sync import create_task

@pytest.mark.asyncio_cooperative
async def test_create_task():
    await create_task(coro=asyncio.sleep(0), name='test')

@pytest.mark.asyncio_cooperative
async def test_persistent_task():
    check = False
    async def task():
        await asyncio.sleep(1)
        nonlocal check
        check = True
    create_task(coro=task(), skip_gc_until_done=True)
    # there is no local reference to the newly created task. does it still complete? 
    await asyncio.sleep(2)
    assert check is True
