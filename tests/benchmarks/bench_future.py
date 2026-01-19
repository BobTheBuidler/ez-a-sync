"""Benchmarks for ASyncFuture operations."""
import pytest
from a_sync.future import ASyncFuture


async def one() -> int:
    return 1


async def two() -> int:
    return 2


async def dct():
    return {1: 2}


@pytest.mark.benchmark
def test_future_result(benchmark):
    """Benchmark ASyncFuture result retrieval."""
    benchmark(lambda: ASyncFuture(one()).result())


@pytest.mark.benchmark
def test_future_add(benchmark):
    """Benchmark ASyncFuture addition operations."""
    benchmark(lambda: ASyncFuture(one()) + ASyncFuture(two()))


@pytest.mark.benchmark
def test_future_arithmetic(benchmark):
    """Benchmark complex arithmetic with ASyncFuture."""
    def arithmetic():
        some = ASyncFuture(two())
        other = ASyncFuture(two())
        stuff = ASyncFuture(two())
        idrk = ASyncFuture(one())
        return (some + stuff - idrk) * ASyncFuture(two())
    
    benchmark(arithmetic)


@pytest.mark.benchmark
def test_future_comparison(benchmark):
    """Benchmark ASyncFuture comparison operations."""
    def comparison():
        f1 = ASyncFuture(one())
        f2 = ASyncFuture(two())
        return f1 < f2 and f2 > f1
    
    benchmark(comparison)


@pytest.mark.benchmark
def test_future_getitem(benchmark):
    """Benchmark ASyncFuture dictionary access."""
    benchmark(lambda: ASyncFuture(dct())[1])
