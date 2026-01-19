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


def test_async_decorator_sync_call():
    """Benchmark @a_sync('async') function called synchronously."""
    result = sync_function(sync=True)
    assert result == 4950


def test_async_decorator_async_call():
    """Benchmark @a_sync('async') function called asynchronously."""
    async def run():
        return await sync_function()
    
    result = asyncio.run(run())
    assert result == 4950


def test_sync_decorator_sync_call():
    """Benchmark @a_sync('sync') function called synchronously."""
    result = async_function()
    assert result == 4950


def test_sync_decorator_async_call():
    """Benchmark @a_sync('sync') function called asynchronously."""
    async def run():
        return await async_function(sync=False)
    
    result = asyncio.run(run())
    assert result == 4950
