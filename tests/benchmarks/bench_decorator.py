"""Benchmarks for @a_sync decorator functionality."""
import asyncio
import pytest
from a_sync import a_sync


@a_sync('async')
def sync_function():
    """A simple sync function decorated as async."""
    return sum(range(100))


@a_sync('sync')
async def async_function():
    """A simple async function decorated as sync."""
    await asyncio.sleep(0)
    return sum(range(100))


@pytest.mark.benchmark
def test_async_decorator_sync_call(benchmark):
    """Benchmark @a_sync('async') function called synchronously."""
    benchmark(lambda: sync_function(sync=True))


@pytest.mark.benchmark
def test_async_decorator_async_call(benchmark):
    """Benchmark @a_sync('async') function called asynchronously."""
    async def run():
        return await sync_function()
    
    benchmark(lambda: asyncio.run(run()))


@pytest.mark.benchmark
def test_sync_decorator_sync_call(benchmark):
    """Benchmark @a_sync('sync') function called synchronously."""
    benchmark(async_function)


@pytest.mark.benchmark
def test_sync_decorator_async_call(benchmark):
    """Benchmark @a_sync('sync') function called asynchronously."""
    async def run():
        return await async_function(sync=False)
    
    benchmark(lambda: asyncio.run(run()))
