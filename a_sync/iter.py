
import asyncio
from typing import AsyncIterable, Iterator, TypeVar

T = TypeVar('T')

class ASyncIterable(AsyncIterable[T]):
    """An iterable that can be used in both a `for` loop and an `async for` loop."""
    def __iter__(self) -> Iterator[T]:
        return self.__sync_iterator()
    def __sync_iterator(self) -> Iterator[T]:
        aiterator = self.__aiter__()
        while True:
            try:
                yield asyncio.get_event_loop().run_until_complete(aiterator.__anext__())
            except StopAsyncIteration as e:
                raise StopIteration(*e.args) from e

class ASyncIterator(ASyncIterable[T]):
    """An iterator that can be used in both a `for` loop and an `async for` loop."""
    def __next__(self) -> T:
        return asyncio.get_event_loop().run_until_complete(self.__anext__())

class ASyncWrappedIterable(ASyncIterable[T]):
    def __init__(self, async_iterable: AsyncIterable[T]):
        self.__iterable = async_iterable.__aiter__()
    def __aiter__(self) -> AsyncIterable[T]:
        return self.__iterable
    
class ASyncWrappedIterator(ASyncWrappedIterable[T], ASyncIterator[T]):
    async def __anext__(self) -> T:
        return await self.__iterable.__anext__()
    
