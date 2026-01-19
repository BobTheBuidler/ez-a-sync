"""Benchmarks for executor operations."""
import asyncio
import time
import pytest
from a_sync.executor import ProcessPoolExecutor


def simple_work(value):
    """Perform simple computation."""
    return value * 2


def io_work(duration):
    """Simulate IO work."""
    time.sleep(duration)
    return duration


def test_executor_submit():
    """Benchmark ProcessPoolExecutor submit operation."""
    executor = ProcessPoolExecutor(2)
    
    async def run():
        fut = executor.submit(simple_work, 42)
        return await fut
    
    result = asyncio.run(run())
    assert result == 84


def test_executor_run():
    """Benchmark ProcessPoolExecutor run operation."""
    executor = ProcessPoolExecutor(2)
    
    async def run():
        return await executor.run(simple_work, 42)
    
    result = asyncio.run(run())
    assert result == 84
