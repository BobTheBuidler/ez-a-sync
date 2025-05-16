from asyncio import TimerHandle

import pytest

from a_sync.iter import ASyncGeneratorFunction, ASyncIterator


def test_a_sync_generator_function_init():
    async def test():
        yield 1
        yield 2

    wrapped = ASyncGeneratorFunction(test)
    assert isinstance(wrapped, ASyncGeneratorFunction)
    assert wrapped.field_name == "test"
    assert wrapped.__wrapped__ is test
    assert wrapped.__weakself__ is None
    assert wrapped._cache_handle is None


def test_a_sync_generator_function_decorate_func():
    @ASyncGeneratorFunction
    async def test():
        yield 1
        yield 2

    assert isinstance(test, ASyncGeneratorFunction)
    assert test.field_name == "test"
    assert test.__weakself__ is None
    assert test._cache_handle is None


def test_a_sync_generator_function_decorate_method():
    class MyClass:
        @ASyncGeneratorFunction
        async def test(self):
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


def test_a_sync_generator_function_call_iter():
    @ASyncGeneratorFunction
    async def test():
        yield 1
        yield 2

    retval = test()
    assert isinstance(retval, ASyncIterator)
    assert list(retval) == [1, 2]


def test_a_sync_generator_method_call_iter():
    class MyClass:
        @ASyncGeneratorFunction
        async def test(self):
            yield 1
            yield 2

    instance = MyClass()
    retval = instance.test()
    assert isinstance(retval, ASyncIterator)
    assert list(retval) == [1, 2]


@pytest.mark.asyncio_cooperative
async def test_a_sync_generator_function_call_aiter():
    @ASyncGeneratorFunction
    async def test():
        yield 1
        yield 2

    retval = test()
    assert isinstance(retval, ASyncIterator)
    assert [x async for x in retval] == [1, 2]


@pytest.mark.asyncio_cooperative
async def test_a_sync_generator_method_call_aiter():
    class MyClass:
        @ASyncGeneratorFunction
        async def test(self):
            yield 1
            yield 2

    instance = MyClass()
    retval = instance.test()
    assert isinstance(retval, ASyncIterator)
    assert [x async for x in retval] == [1, 2]


@pytest.mark.asyncio_cooperative
async def test_a_sync_generator_function_call_await():
    @ASyncGeneratorFunction
    async def test():
        yield 1
        yield 2

    retval = test()
    assert isinstance(retval, ASyncIterator)
    assert await retval == [1, 2]


@pytest.mark.asyncio_cooperative
async def test_a_sync_generator_method_call_await():
    class MyClass:
        @ASyncGeneratorFunction
        async def test(self):
            yield 1
            yield 2

    instance = MyClass()
    retval = instance.test()
    assert isinstance(retval, ASyncIterator)
    assert await retval == [1, 2]
