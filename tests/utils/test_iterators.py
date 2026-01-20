import asyncio
from collections.abc import AsyncIterator, Callable, Iterable
from typing import Any, Generic, TypeVar, cast

from typing_extensions import override

import pytest

from a_sync.utils.iterators import _Done, as_yielded

T = TypeVar("T")
_F = TypeVar("_F", bound=Callable[..., Any])
asyncio_cooperative = cast(Callable[[_F], _F], pytest.mark.asyncio_cooperative)


# Helpers
class AsyncGen(Generic[T]):
    def __init__(self, values: Iterable[T], delay: float = 0) -> None:
        self.values = list(values)
        self.delay = delay
        self._idx = 0

    def __aiter__(self) -> "AsyncGen[T]":
        self._idx = 0
        return self

    async def __anext__(self) -> T:
        if self._idx >= len(self.values):
            raise StopAsyncIteration
        val = self.values[self._idx]
        self._idx += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return val


class ErrorGen(AsyncIterator[object]):
    @override
    def __aiter__(self) -> "ErrorGen":
        return self

    @override
    async def __anext__(self) -> object:
        raise Exception("Iterator Error!")


@asyncio_cooperative
async def test_simple_merge() -> None:
    gen1 = AsyncGen([1, 2, 3])
    gen2 = AsyncGen([10, 20])
    results: set[int] = set()
    async for item in as_yielded(gen1, gen2):
        results.add(item)
    assert results == {1, 2, 3, 10, 20}


@asyncio_cooperative
async def test_merge_with_empty() -> None:
    gen_empty = AsyncGen[int]([])
    gen_full = AsyncGen([5])
    results: list[int] = []
    async for item in as_yielded(gen_empty, gen_full):
        results.append(item)
    assert results == [5]


@asyncio_cooperative
async def test_merge_slow_fast() -> None:
    fast = AsyncGen([1, 2, 3], delay=0.01)
    slow = AsyncGen(["a", "b"], delay=0.05)
    got: list[int | str] = []
    async for item in as_yielded(fast, slow):
        got.append(item)
    # All should appear, timing for order is implementation dependent.
    assert set(got) == {1, 2, 3, "a", "b"}


@asyncio_cooperative
async def test_error_in_iterator() -> None:
    error_gen = ErrorGen()
    ok_gen = AsyncGen([4, 5])
    got: list[int] = []
    with pytest.raises(Exception, match="Iterator Error!"):
        async for item in as_yielded(error_gen, ok_gen):
            got.append(item)


@asyncio_cooperative
async def test_single_iterator() -> None:
    gen = AsyncGen(range(5))
    results: list[int] = []
    async for item in as_yielded(gen):
        results.append(item)
    assert results == [0, 1, 2, 3, 4]


@asyncio_cooperative
async def test_all_empty_iterators() -> None:
    gens = [AsyncGen[int]([]) for _ in range(3)]
    results: list[int] = []
    async for item in as_yielded(*gens):
        results.append(item)
    assert results == []


@asyncio_cooperative
async def test_consumer_cancels_early() -> None:
    # If the consumer stops early, as_yielded should not misbehave or deadlock.
    gen = AsyncGen(range(100))
    count = 0
    async for item in as_yielded(gen):
        count += 1
        if count >= 5:
            break
    assert count == 5


def test_done_repr_no_exception() -> None:
    done = _Done()
    assert repr(done) == "a_sync.utils.iterators._Done(exc=None)"


def test_done_repr_with_exception() -> None:
    exc = ValueError("bad input")
    done = _Done(exc)
    assert repr(done) == "a_sync.utils.iterators._Done(exc=ValueError('bad input'))"


def test_done_tb_returns_exception_traceback() -> None:
    def raise_error() -> None:
        raise ValueError("traceback test")

    try:
        raise_error()
    except ValueError as exc:
        done = _Done(exc)
        assert done._tb is exc.__traceback__
