"""Benchmarks for ASyncFuture operations."""
import pytest
from a_sync.future import ASyncFuture


async def one() -> int:
    return 1


async def two() -> int:
    return 2


async def dct():
    return {1: 2}


def test_future_result():
    """Benchmark ASyncFuture result retrieval."""
    result = ASyncFuture(one()).result()
    assert result == 1


def test_future_add():
    """Benchmark ASyncFuture addition operations."""
    result = ASyncFuture(one()) + ASyncFuture(two())
    assert result == 3


def test_future_arithmetic():
    """Benchmark complex arithmetic with ASyncFuture."""
    some = ASyncFuture(two())
    other = ASyncFuture(two())
    stuff = ASyncFuture(two())
    idrk = ASyncFuture(one())
    result = (some + stuff - idrk) * ASyncFuture(two())
    assert result == 6


def test_future_comparison():
    """Benchmark ASyncFuture comparison operations."""
    f1 = ASyncFuture(one())
    f2 = ASyncFuture(two())
    assert f1 < f2 and f2 > f1


def test_future_getitem():
    """Benchmark ASyncFuture dictionary access."""
    result = ASyncFuture(dct())[1]
    assert result == 2
