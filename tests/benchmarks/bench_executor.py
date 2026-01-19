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


@pytest.mark.benchmark
def test_executor_submit(benchmark):
    """Benchmark ProcessPoolExecutor submit operation."""
    executor = ProcessPoolExecutor(2)
    
    async def run():
        fut = executor.submit(simple_work, 42)
        return await fut
    
    benchmark(lambda: asyncio.run(run()))


@pytest.mark.benchmark
def test_executor_run(benchmark):
    """Benchmark ProcessPoolExecutor run operation."""
    executor = ProcessPoolExecutor(2)
    
    async def run():
        return await executor.run(simple_work, 42)
    
    benchmark(lambda: asyncio.run(run()))
