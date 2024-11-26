import asyncio
import pytest

from a_sync import Semaphore, apply_semaphore
from a_sync.exceptions import FunctionNotAsync


@pytest.mark.asyncio_cooperative
async def test_apply_semaphore_int():
    apply_semaphore(asyncio.sleep, 1)


@pytest.mark.asyncio_cooperative
async def test_apply_semaphore_asyncio_semaphore():
    apply_semaphore(asyncio.sleep, asyncio.Semaphore(1))


@pytest.mark.asyncio_cooperative
async def test_apply_semaphore_a_sync_semaphore():
    apply_semaphore(asyncio.sleep, Semaphore(1))


def fail():
    pass


@pytest.mark.asyncio_cooperative
async def test_apply_semaphore_failure_int():
    with pytest.raises(FunctionNotAsync):
        apply_semaphore(fail, 1)


@pytest.mark.asyncio_cooperative
async def test_apply_semaphore_failure_asyncio_semaphore():
    with pytest.raises(FunctionNotAsync):
        apply_semaphore(fail, asyncio.Semaphore(1))


@pytest.mark.asyncio_cooperative
async def test_apply_semaphore_failure_a_sync_semaphore():
    with pytest.raises(FunctionNotAsync):
        apply_semaphore(fail, Semaphore(1))
