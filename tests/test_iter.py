

import pytest

from a_sync.iter import (ASyncIterable, ASyncIterator, ASyncWrappedIterable,
                         ASyncWrappedIterator)


async def async_gen():
    yield 0
    yield 1
    yield 2

def test_iterable_wrap():
    assert isinstance(ASyncIterable.wrap(async_gen()), ASyncWrappedIterable)

def test_iterator_wrap():
    assert isinstance(ASyncIterator.wrap(async_gen()), ASyncWrappedIterator)

def test_iterable_sync():
    assert [i for i in ASyncIterable.wrap(async_gen())] == [0, 1, 2]

@pytest.mark.asyncio_cooperative
async def test_iterable_async():
    assert [i async for i in ASyncIterable.wrap(async_gen())] == [0, 1, 2]

def test_iterator_sync():
    iterator = ASyncIterator.wrap(async_gen())
    for i in range(4):
        if i < 3:
            assert next(iterator) == i
        else:
            with pytest.raises(StopIteration):
                next(iterator)

@pytest.mark.asyncio_cooperative   
async def test_iterator_async():
    iterator = ASyncIterator.wrap(async_gen())
    for i in range(4):
        if i < 3:
            assert await iterator.__anext__() == i
        else:
            with pytest.raises(StopAsyncIteration):
                await iterator.__anext__()
