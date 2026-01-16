from asyncio import TimerHandle
from collections.abc import AsyncIterator, Callable
from typing import Any, TypeVar, cast

import pytest

from a_sync.iter import ASyncGeneratorFunction, ASyncIterator

_F = TypeVar("_F", bound=Callable[..., Any])
asyncio_cooperative = cast(Callable[[_F], _F], pytest.mark.asyncio_cooperative)


def test_a_sync_generator_function_init() -> None:
    async def test() -> AsyncIterator[int]:
        yield 1
        yield 2

    wrapped = ASyncGeneratorFunction(test)
    assert isinstance(wrapped, ASyncGeneratorFunction)
    assert wrapped.field_name == "test"
    assert wrapped.__wrapped__ is test
    assert wrapped.__weakself__ is None
    assert wrapped._cache_handle is None


def test_a_sync_generator_function_decorate_func() -> None:
    @ASyncGeneratorFunction
    async def test() -> AsyncIterator[int]:
        yield 1
        yield 2

    assert isinstance(test, ASyncGeneratorFunction)
    assert test.field_name == "test"
    assert test.__weakself__ is None
    assert test._cache_handle is None


def test_a_sync_generator_function_decorate_method() -> None:
    class MyClass:
        @ASyncGeneratorFunction
        async def test(self) -> AsyncIterator[int]:
            yield 1
            yield 2

    assert isinstance(MyClass.test, ASyncGeneratorFunction)
    assert MyClass.test.field_name == "test"
    assert MyClass.test.__weakself__ is None
    assert MyClass.test._cache_handle is None

    instance = MyClass()
    assert isinstance(instance.test, ASyncGeneratorFunction)
    assert instance.test.field_name == "test"
    assert instance.test.__wrapped__.__name__ == "test"
    assert instance.test.__weakself__ is not None
    assert instance.test.__self__ is instance.test.__weakself__() is instance
    assert isinstance(instance.test._cache_handle, TimerHandle)


def test_a_sync_generator_function_call_iter() -> None:
    @ASyncGeneratorFunction
    async def test() -> AsyncIterator[int]:
        yield 1
        yield 2

    retval = test()
    assert isinstance(retval, ASyncIterator)
    assert list(retval) == [1, 2]


def test_a_sync_generator_method_call_iter() -> None:
    class MyClass:
        @ASyncGeneratorFunction
        async def test(self) -> AsyncIterator[int]:
            yield 1
            yield 2

    instance = MyClass()
    retval = cast(Any, instance.test)()
    assert isinstance(retval, ASyncIterator)
    assert list(retval) == [1, 2]


@asyncio_cooperative
async def test_a_sync_generator_function_call_aiter() -> None:
    @ASyncGeneratorFunction
    async def test() -> AsyncIterator[int]:
        yield 1
        yield 2

    retval = test()
    assert isinstance(retval, ASyncIterator)
    assert [x async for x in retval] == [1, 2]


@asyncio_cooperative
async def test_a_sync_generator_method_call_aiter() -> None:
    class MyClass:
        @ASyncGeneratorFunction
        async def test(self) -> AsyncIterator[int]:
            yield 1
            yield 2

    instance = MyClass()
    retval = cast(Any, instance.test)()
    assert isinstance(retval, ASyncIterator)
    assert [x async for x in retval] == [1, 2]


@asyncio_cooperative
async def test_a_sync_generator_function_call_await() -> None:
    @ASyncGeneratorFunction
    async def test() -> AsyncIterator[int]:
        yield 1
        yield 2

    retval = test()
    assert isinstance(retval, ASyncIterator)
    assert await retval == [1, 2]


@asyncio_cooperative
async def test_a_sync_generator_method_call_await() -> None:
    class MyClass:
        @ASyncGeneratorFunction
        async def test(self) -> AsyncIterator[int]:
            yield 1
            yield 2

    instance = MyClass()
    retval = cast(Any, instance.test)()
    assert isinstance(retval, ASyncIterator)
    assert await retval == [1, 2]
