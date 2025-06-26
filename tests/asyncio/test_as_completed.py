"""
Tests for the :func:`a_sync.asyncio.as_completed` helper function.

This test module verifies the behavior of :func:`a_sync.asyncio.as_completed` from the
``a_sync.asyncio`` module. Important: when using :func:`as_completed` in synchronous mode
(i.e. with aiter=False), the iterator yields awaitable objects rather than the final results.
Therefore, each yielded item must be explicitly awaited in order to obtain its result.
Similarly, when a mapping of awaitables is provided, each yielded awaitable (in non‐async iteration)
returns a tuple (key, value) that must be awaited to extract the actual key and value.

Examples:
    For a list of awaitables:
        tasks = [sample_task(i) for i in range(5)]
        results = [await result for result in a_sync.as_completed(tasks, aiter=False)]
        # Each item is an awaitable; you must await it to obtain the numeric result.

    For a mapping of awaitables:
        tasks = {"task1": sample_task(1), "task2": sample_task(2)}
        results = {}
        for result in a_sync.as_completed(tasks, aiter=False):
            key, value = await result
            results[key] = value
        # Here, the yielded values are awaitables that return (key, value) tuples when awaited.

See Also:
    - :func:`a_sync.asyncio.as_completed`
"""

import asyncio
import a_sync
import pytest

from tests.fixtures import sample_exc, sample_task, timeout_task


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_awaitables():
    tasks = [sample_task(i) for i in range(5)]
    results = [await result for result in a_sync.as_completed(tasks, aiter=False)]
    assert sorted(results) == list(range(5)), "Results should be in ascending order from 0 to 4"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_awaitables_aiter():
    tasks = [sample_task(i) for i in range(5)]
    results = []
    async for result in a_sync.as_completed(tasks, aiter=True):
        results.append(result)
    assert sorted(results) == list(range(5)), "Results should be in ascending order from 0 to 4"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_mapping():
    tasks = {"task1": sample_task(1), "task2": sample_task(2)}
    results = {}
    for result in a_sync.as_completed(tasks, aiter=False):
        key, value = await result
        results[key] = value
    assert results == {"task1": 1, "task2": 2}, "Results should match the input mapping"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_mapping_aiter():
    tasks = {"task1": sample_task(1), "task2": sample_task(2)}
    results = {}
    async for key, result in a_sync.as_completed(tasks, aiter=True):
        results[key] = result
    assert results == {"task1": 1, "task2": 2}, "Results should match the input mapping"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_timeout():
    tasks = [timeout_task(i) for i in range(2)]
    with pytest.raises(asyncio.TimeoutError):
        [await result for result in a_sync.as_completed(tasks, aiter=False, timeout=0.05)]


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_timeout_aiter():
    tasks = [timeout_task(i) for i in range(2)]
    with pytest.raises(asyncio.TimeoutError):
        [result async for result in a_sync.as_completed(tasks, aiter=True, timeout=0.05)]


@pytest.mark.asyncio_cooperative
async def test_as_completed_return_exceptions():
    tasks = [sample_exc(i) for i in range(1)]
    results = [
        await result for result in a_sync.as_completed(tasks, aiter=False, return_exceptions=True)
    ]
    assert isinstance(results[0], ValueError), f"The result should be an exception {results}"


@pytest.mark.asyncio_cooperative
async def test_as_completed_return_exceptions_aiter():
    tasks = [sample_exc(i) for i in range(1)]
    results = []
    async for result in a_sync.as_completed(tasks, aiter=True, return_exceptions=True):
        results.append(result)
    assert isinstance(results[0], ValueError), "The result should be an exception"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_tqdm_disabled():
    tasks = [sample_task(i) for i in range(5)]
    results = [await result for result in a_sync.as_completed(tasks, aiter=False, tqdm=False)]
    assert sorted(results) == list(range(5)), "Results should be in ascending order from 0 to 4"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_tqdm_disabled_aiter():
    tasks = [sample_task(i) for i in range(5)]
    results = []
    async for result in a_sync.as_completed(tasks, aiter=True, tqdm=False):
        results.append(result)
    assert sorted(results) == list(range(5)), "Results should be in ascending order from 0 to 4"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_mapping_and_return_exceptions():
    tasks = {"task1": sample_exc(1), "task2": sample_task(2)}
    results = {}
    for result in a_sync.as_completed(tasks, return_exceptions=True, aiter=False):
        key, value = await result
        results[key] = value
    assert isinstance(results["task1"], ValueError), "Result should be ValueError"
    assert results["task2"] == 2, "Results should match the input mapping"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_mapping_and_return_exceptions_aiter():
    tasks = {"task1": sample_exc(1), "task2": sample_task(2)}
    results = {}
    async for key, result in a_sync.as_completed(tasks, return_exceptions=True, aiter=True):
        results[key] = result
    assert isinstance(results["task1"], ValueError), "Result should be ValueError"
    assert results["task2"] == 2, "Results should match the input mapping"