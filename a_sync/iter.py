
import asyncio
import functools
import inspect
import logging
from a_sync._typing import *


logger = logging.getLogger(__name__)

class ASyncIterable(AsyncIterable[T], Iterable[T]):
    """A hybrid Iterable/AsyncIterable implementation that can be used in both a `for` loop and an `async for` loop."""
    @classmethod
    def wrap(cls, wrapped: AsyncIterable[T]) -> "ASyncIterable[T]":
        # NOTE: for backward-compatability only. Will be removed soon.
        logger.warning("ASyncIterable.wrap will be removed soon. Please replace uses with simple instantiation ie `ASyncIterable(wrapped)`")
        return cls(wrapped)
    def __init__(self, async_iterable: AsyncIterable[T]):
        self.__wrapped__ = async_iterable
    def __repr__(self) -> str:
        return f"<{type(self).__name__} for {self.__wrapped__} at {hex(id(self))}>"
    def __iter__(self) -> Iterator[T]:
        yield from ASyncIterator(self.__aiter__())
    def __aiter__(self) -> AsyncIterator[T]:
        return self.__wrapped__.__aiter__()
    __slots__ = "__wrapped__", 

AsyncGenFunc = Callable[P, AsyncGenerator[T, None]]

class ASyncIterator(AsyncIterator[T], Iterator[T]):
    """A hybrid Iterator/AsyncIterator implementation that can be used in both a `for` loop and an `async for` loop."""
    def __next__(self) -> T:
        try:
            return asyncio.get_event_loop().run_until_complete(self.__anext__())
        except StopAsyncIteration as e:
            raise StopIteration from e
    @overload
    def wrap(cls, aiterator: AsyncIterator[T]) -> "ASyncIterator[T]":...
    @overload
    def wrap(cls, async_gen_func: AsyncGenFunc[P, T]) -> "ASyncGeneratorFunction[P, T]":...
    @classmethod
    def wrap(cls, wrapped):
        if isinstance(wrapped, AsyncIterator):
            logger.warning("This use case for ASyncIterator.wrap will be removed soon. Please replace uses with simple instantiation ie `ASyncIterator(wrapped)`")
            return cls(wrapped)
        elif inspect.isasyncgenfunction(wrapped):
            return ASyncGeneratorFunction(wrapped)
        raise TypeError(f"`wrapped` must be an AsyncIterator or an async generator function. You passed {wrapped}")
    def __init__(self, async_iterator: AsyncIterator[T]):
        self.__wrapped__ = async_iterator
    async def __anext__(self) -> T:
        return await self.__wrapped__.__anext__()

class ASyncGeneratorFunction(Generic[P, T]):
    __slots__ = "__wrapped__", 
    def __init__(self, async_gen_func: AsyncGenFunc[P, T]) -> None:
        self.__wrapped__ = async_gen_func
        functools.update_wrapper(self, self.__wrapped__)
        assert inspect.isasyncgenfunction(self)
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> ASyncIterator[T]:
        return ASyncIterator(self.__wrapped__(*args, **kwargs))
    