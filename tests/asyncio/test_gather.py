import asyncio

import pytest

from a_sync import gather
from tests.fixtures import sample_exc


async def sample_task(number):
    await asyncio.sleep(0.1)
    return number * 2


@pytest.mark.asyncio_cooperative
async def test_gather_with_awaitables():
    results = await gather(sample_task(1), sample_task(2), sample_task(3))
    assert results == [2, 4, 6]


@pytest.mark.asyncio_cooperative
async def test_gather_with_awaitables_and_tqdm():
    results = await gather(sample_task(1), sample_task(2), sample_task(3), tqdm=True)
    assert results == [2, 4, 6]


@pytest.mark.asyncio_cooperative
async def test_gather_with_mapping_and_tqdm():
    tasks = {"a": sample_task(1), "b": sample_task(2), "c": sample_task(3)}
    results = await gather(tasks, tqdm=True)
    assert results == {"a": 2, "b": 4, "c": 6}


@pytest.mark.asyncio_cooperative
async def test_gather_with_exceptions():
    with pytest.raises(ValueError):
        await gather(sample_exc(None))


@pytest.mark.asyncio_cooperative
async def test_gather_with_return_exceptions():
    results = await gather(sample_exc(None), return_exceptions=True)
    assert isinstance(results[0], ValueError)


@pytest.mark.asyncio_cooperative
async def test_gather_with_return_exceptions_and_tqdm():
    results = await gather(sample_exc(None), return_exceptions=True, tqdm=True)
    assert isinstance(results[0], ValueError)
