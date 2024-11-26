import asyncio
import pytest

from a_sync import Semaphore, apply_semaphore


@pytest.mark.asyncio_cooperative
async def test_apply_semaphore_int():
    apply_semaphore(asyncio.sleep, 1)

@pytest.mark.asyncio_cooperative
async def test_apply_semaphore_asyncio_semaphore():
    apply_semaphore(asyncio.sleep, asyncio.Semaphore(1))

@pytest.mark.asyncio_cooperative
async def test_apply_semaphore_a_sync_semaphore():
    apply_semaphore(asyncio.sleep, Semaphore(1))
