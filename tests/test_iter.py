import asyncio
import contextlib
import pytest
import time
from typing import AsyncIterator, Iterator

from a_sync.a_sync.base import ASyncGenericBase
from a_sync.exceptions import SyncModeInAsyncContextError
from a_sync.iter import ASyncIterable, ASyncIterator


test_both = pytest.mark.parametrize("cls_to_test", [ASyncIterable, ASyncIterator])


@pytest.fixture
def async_generator():
    async def async_gen(i: int = 3):
        for i in range(i):
            yield i

    yield async_gen


@pytest.fixture
def async_generator_empty():
    async def async_gen_empty():
        if True:
            return
        yield

    yield async_gen_empty


@pytest.fixture
def async_error_generator():
    async def async_err_gen():
        yield 0
        yield 1
        raise ValueError("Simulated error")

    return async_err_gen


@test_both
def test_wrap_types(cls_to_test, async_generator):
    assert isinstance(cls_to_test(async_generator()), cls_to_test)
    assert isinstance(cls_to_test.wrap(async_generator()), cls_to_test)


@test_both
def test_sync(cls_to_test, async_generator):
    # sourcery skip: identity-comprehension, list-comprehension
    # comprehension
    assert [i for i in cls_to_test(async_generator())] == [0, 1, 2]

    # iteration
    result = []
    for item in cls_to_test(async_generator()):
        result.append(item)
    assert result == [0, 1, 2]

    # wrap
    assert list(cls_to_test.wrap(async_generator())) == [0, 1, 2]

    # list
    assert list(cls_to_test(async_generator())) == [0, 1, 2]

    # helper method
    assert cls_to_test(async_generator()).materialized == [0, 1, 2]
    assert cls_to_test.wrap(async_generator()).materialized == [0, 1, 2]


@test_both
@pytest.mark.asyncio_cooperative
async def test_async(cls_to_test, async_generator):
    ait = cls_to_test(async_generator())

    # comprehension
    with pytest.raises(
        SyncModeInAsyncContextError,
        match="The event loop is already running. Try iterating using `async for` instead of `for`.",
    ):
        list(ait)
    assert [i async for i in ait] == [0, 1, 2]

    # iteration
    result = []
    async for item in cls_to_test(async_generator()):
        result.append(item)
    assert result == [0, 1, 2]
    with pytest.raises(
        SyncModeInAsyncContextError,
        match="The event loop is already running. Try iterating using `async for` instead of `for`.",
    ):
        for _ in cls_to_test(async_generator()):
            pass

    # await
    assert await cls_to_test(async_generator()) == [0, 1, 2]

    # wrap
    assert [i async for i in cls_to_test.wrap(async_generator())] == [0, 1, 2]
    assert await cls_to_test.wrap(async_generator()) == [0, 1, 2]


@test_both
def test_sync_empty(cls_to_test, async_generator_empty):
    assert not list(cls_to_test(async_generator_empty()))


@test_both
@pytest.mark.asyncio_cooperative
async def test_async_empty(cls_to_test, async_generator_empty):
    ait = cls_to_test(async_generator_empty())
    with pytest.raises(
        SyncModeInAsyncContextError,
        match="The event loop is already running. Try iterating using `async for` instead of `for`.",
    ):
        list(ait)
    assert not [i async for i in ait]


@test_both
def test_sync_partial(cls_to_test, async_generator):
    iterator = cls_to_test(async_generator(5))
    results = []
    for item in iterator:
        results.append(item)
        if item == 2:
            break
    assert results == [0, 1, 2]

    # Ensure the iterator can still be used after cancellation
    remaining = list(iterator)
    assert remaining == [3, 4] if cls_to_test is ASyncIterator else [0, 1, 2, 3, 4]


@test_both
@pytest.mark.asyncio_cooperative
async def test_async_partial(cls_to_test, async_generator):
    iterator = cls_to_test(async_generator(5))
    results = []
    async for item in iterator:
        results.append(item)
        if item == 2:
            break
    assert results == [0, 1, 2]

    # Ensure the iterator can still be used after cancellation
    remaining = [item async for item in iterator]
    assert remaining == [3, 4] if cls_to_test is ASyncIterator else [0, 1, 2, 3, 4]


@test_both
def test_stop_iteration_sync(cls_to_test, async_generator):
    it = cls_to_test(async_generator())
    if cls_to_test is ASyncIterable:
        it = it.__iter__()
    for i in range(4):
        if i < 3:
            assert next(it) == i
        else:
            with pytest.raises(StopIteration):
                next(it)


@test_both
@pytest.mark.asyncio_cooperative
async def test_stop_iteration_async(cls_to_test, async_generator):
    ait = cls_to_test(async_generator())
    if cls_to_test is ASyncIterable:
        ait = ait.__aiter__()
    for i in range(4):
        if i < 3:
            assert await ait.__anext__() == i
        else:
            with pytest.raises(StopAsyncIteration):
                await ait.__anext__()


# Test decorator


def test_aiterable_decorated_func_sync():
    with pytest.raises(
        TypeError, match="`async_iterable` must be an AsyncIterable. You passed "
    ):

        @ASyncIterable.wrap
        async def decorated():
            yield 0


@pytest.mark.asyncio_cooperative
async def test_aiterable_decorated_func_async(async_generator):
    with pytest.raises(
        TypeError, match="`async_iterable` must be an AsyncIterable. You passed "
    ):

        @ASyncIterable.wrap
        async def decorated():
            yield 0


def test_aiterator_decorated_func_sync(async_generator):
    @ASyncIterator.wrap
    async def decorated():
        async for i in async_generator():
            yield i

    retval = decorated()
    assert isinstance(retval, ASyncIterator)
    assert list(retval) == [0, 1, 2]


@pytest.mark.asyncio_cooperative
async def test_aiterator_decorated_func_async(async_generator):
    @ASyncIterator.wrap
    async def decorated():
        async for i in async_generator():
            yield i

    retval = decorated()
    assert isinstance(retval, ASyncIterator)
    assert await retval == [0, 1, 2]


def test_aiterable_decorated_method_sync():
    with pytest.raises(TypeError, match=""):

        class Test:
            @ASyncIterable.wrap
            async def decorated(self):
                yield 0


@pytest.mark.asyncio_cooperative
async def test_aiterable_decorated_method_async():
    with pytest.raises(TypeError, match=""):

        class Test:
            @ASyncIterable.wrap
            async def decorated(self):
                yield 0


def test_aiterator_decorated_method_sync(async_generator):
    class Test:
        @ASyncIterator.wrap
        async def decorated(self):
            async for i in async_generator():
                yield i

    retval = Test().decorated()
    assert isinstance(retval, ASyncIterator)
    assert list(retval) == [0, 1, 2]


@pytest.mark.asyncio_cooperative
async def test_aiterator_decorated_method_async(async_generator):
    class Test:
        @ASyncIterator.wrap
        async def decorated(self):
            async for i in async_generator():
                yield i

    retval = Test().decorated()
    assert isinstance(retval, ASyncIterator)
    assert await retval == [0, 1, 2]


@test_both
def test_sync_error_handling(cls_to_test, async_error_generator):
    ait = cls_to_test(async_error_generator())
    results = []
    with pytest.raises(ValueError, match="Simulated error"):
        results.extend(iter(ait))
    # we still got some results though
    assert results == [0, 1]


@test_both
@pytest.mark.asyncio_cooperative
async def test_async_error_handling(cls_to_test, async_error_generator):
    ait = cls_to_test(async_error_generator())
    results = []
    with pytest.raises(ValueError, match="Simulated error"):
        async for item in ait:
            results.append(item)
    # we still got some results though
    assert results == [0, 1]


# Test failures


@test_both
def test_sync_with_iterable(cls_to_test):
    with pytest.raises(TypeError):
        cls_to_test([0, 1, 2])


@test_both
@pytest.mark.asyncio_cooperative
async def test_async_with_iterable(cls_to_test):
    with pytest.raises(TypeError):
        cls_to_test([0, 1, 2])


# Type check dunder methods


def test_async_iterable_iter_method(async_generator):
    ait = ASyncIterable(async_generator())
    iterator = iter(ait)
    assert isinstance(iterator, Iterator)


def test_async_iterator_iter_method(async_generator):
    ait = ASyncIterator(async_generator())
    iterator = iter(ait)
    assert iterator is ait  # Should return self


@pytest.mark.asyncio_cooperative
async def test_async_aiter_method(async_generator):
    ait = ASyncIterable(async_generator())
    async_iterator = ait.__aiter__()
    assert isinstance(async_iterator, AsyncIterator)


@pytest.mark.asyncio_cooperative
async def test_async_iterator_aiter_method(async_generator):
    ait = ASyncIterator(async_generator())
    async_iterator = ait.__aiter__()
    assert async_iterator is ait  # Should return self
