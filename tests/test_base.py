import asyncio
import time

import pytest

from a_sync.a_sync import HiddenMethod
from a_sync.a_sync.base import ASyncGenericBase
from a_sync.a_sync._meta import ASyncMeta
from a_sync.a_sync.method import ASyncBoundMethodAsyncDefault
from a_sync.exceptions import SyncModeInAsyncContextError
from tests.fixtures import (
    TestClass,
    TestInheritor,
    TestMeta,
    increment,
    TestSync,
    WrongThreadError,
)


def test_base_direct_init():
    with pytest.raises(NotImplementedError, match=""):
        ASyncGenericBase()


classes = pytest.mark.parametrize("cls", [TestClass, TestSync, TestInheritor, TestMeta])

both_modes = pytest.mark.parametrize("sync", [True, False])


@classes
@both_modes
def test_inheritance(cls, sync: bool):
    instance = cls(1, sync=sync)
    assert isinstance(instance, ASyncGenericBase)
    assert isinstance(instance.__class__, ASyncMeta)


@classes
@increment
def test_method_sync(cls: type, i: int):
    sync_instance = cls(i, sync=True)
    assert sync_instance.test_fn() == i

    # Can we override with kwargs?
    assert sync_instance.test_fn(sync=True) == i
    assert sync_instance.test_fn(asynchronous=False) == i
    assert asyncio.iscoroutine(sync_instance.test_fn(sync=False))
    assert asyncio.iscoroutine(sync_instance.test_fn(asynchronous=True))
    if isinstance(sync_instance, TestSync):
        # this raises an assertion error inside of the test_fn execution. this is okay.
        with pytest.raises(WrongThreadError):
            asyncio.get_event_loop().run_until_complete(
                sync_instance.test_fn(sync=False)
            )
        with pytest.raises(WrongThreadError):
            asyncio.get_event_loop().run_until_complete(
                sync_instance.test_fn(asynchronous=True)
            )
    else:
        assert isinstance(
            asyncio.get_event_loop().run_until_complete(
                sync_instance.test_fn(sync=False)
            ),
            int,
        )
        assert isinstance(
            asyncio.get_event_loop().run_until_complete(
                sync_instance.test_fn(asynchronous=True)
            ),
            int,
        )


@classes
@increment
@pytest.mark.asyncio_cooperative
async def test_method_async(cls: type, i: int):
    async_instance = cls(i, sync=False)
    if isinstance(async_instance, TestSync):
        # this raises an assertion error inside of the test_fn execution. this is okay.
        with pytest.raises(WrongThreadError):
            assert await async_instance.test_fn() == i

        # Can we override with kwargs?
        with pytest.raises(WrongThreadError):
            async_instance.test_fn(sync=True)
        with pytest.raises(WrongThreadError):
            async_instance.test_fn(asynchronous=False)

        #    # NOTE this shoudl probbaly run sync in main thread instead of raising...
        #    with pytest.raises(RuntimeError):
        #        await async_instance.test_fn()
    else:
        assert await async_instance.test_fn() == i

        # Can we override with kwargs?
        # Does it fail if we run it synchronously with the event loop running?
        with pytest.raises(SyncModeInAsyncContextError):
            async_instance.test_fn(sync=True)
        with pytest.raises(SyncModeInAsyncContextError):
            async_instance.test_fn(asynchronous=False)


@classes
@increment
def test_property_sync(cls: type, i: int):
    sync_instance = cls(i, sync=True)
    assert sync_instance.test_property == i * 2

    # Can we access hidden methods for properties?
    getter = sync_instance.__test_property__
    assert isinstance(getter, HiddenMethod), getter
    getter_coro = getter()
    assert asyncio.iscoroutine(getter_coro), getter_coro
    assert asyncio.get_event_loop().run_until_complete(getter_coro) == i * 2


@classes
@increment
@pytest.mark.asyncio_cooperative
async def test_property_async(cls: type, i: int):
    async_instance = cls(i, sync=False)
    assert await async_instance.test_property == i * 2

    # Can we access hidden methods for properties?
    getter = async_instance.__test_property__
    assert isinstance(getter, HiddenMethod), getter
    getter_coro = getter()
    assert asyncio.iscoroutine(getter_coro), getter_coro
    assert await getter_coro == i * 2
    with pytest.raises(SyncModeInAsyncContextError):
        await getter(sync=True)


@classes
@increment
def test_cached_property_sync(cls: type, i: int):
    sync_instance = cls(i, sync=True)
    start = time.time()
    assert sync_instance.test_cached_property == i * 3
    assert isinstance(sync_instance.test_cached_property, int)
    duration = time.time() - start
    assert (
        duration < 3
    ), "There is a 2 second sleep in 'test_cached_property' but it should only run once."

    # Can we access hidden methods for properties?
    start = time.time()
    getter = sync_instance.__test_cached_property__
    assert isinstance(getter, HiddenMethod), getter
    getter_coro = getter()
    assert asyncio.iscoroutine(getter_coro), getter_coro
    assert asyncio.get_event_loop().run_until_complete(getter_coro) == i * 3

    # Can we override them too?
    assert (
        asyncio.get_event_loop().run_until_complete(
            sync_instance.__test_cached_property__(sync=False)
        )
        == i * 3
    )
    duration = time.time() - start
    assert (
        duration < 3
    ), "There is a 2 second sleep in 'test_cached_property' but it should only run once."


@classes
@increment
@pytest.mark.asyncio_cooperative
async def test_cached_property_async(cls: type, i: int):
    async_instance = cls(i, sync=False)
    start = time.time()
    assert await async_instance.test_cached_property == i * 3

    # Can we access hidden methods for properties?
    getter = async_instance.__test_cached_property__
    assert isinstance(getter, HiddenMethod), getter
    getter_coro = getter()
    assert asyncio.iscoroutine(getter_coro), getter_coro
    assert await getter_coro == i * 3

    # Can we override them too?
    with pytest.raises(SyncModeInAsyncContextError):
        getter(sync=True)
    assert await async_instance.__test_cached_property__(sync=False) == i * 3

    # Did it only run once?
    duration = time.time() - start
    # For TestSync, the duration can be higher because the calls execute inside of a threadpool which limits the amount of concurrency.
    target_duration = 5 if isinstance(async_instance, TestSync) else 2.1
    assert (
        duration < target_duration
    ), "There is a 2 second sleep in 'test_cached_property' but it should only run once."


@pytest.mark.asyncio_cooperative
async def test_asynchronous_context_manager():
    # Can the implementation work with an async context manager?
    class AsyncContextManager(ASyncGenericBase):
        async def __aenter__(self):
            self.entered = True
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.exited = True

    async with AsyncContextManager() as cm:
        assert cm.entered
    assert cm.exited


def test_synchronous_context_manager():
    # Can the implementation work with a context manager?

    class SyncContextManager(ASyncGenericBase):
        def __enter__(self):
            self.entered = True
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.exited = True

    with SyncContextManager() as cm:
        assert cm.entered
    assert cm.exited


@pytest.mark.asyncio_cooperative
async def test_asynchronous_iteration():
    # Does the implementation screw anything up with aiteration?
    class ASyncObjectWithAiter(ASyncGenericBase):
        def __init__(self):
            self.count = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.count < 3:
                self.count += 1
                return self.count
            raise StopAsyncIteration

    assert [item async for item in ASyncObjectWithAiter()] == [1, 2, 3]


def test_synchronous_iteration():
    # Does the implementation screw anything up with iteration?
    class ASyncObjectWithIter(ASyncGenericBase):
        def __init__(self):
            self.count = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.count < 3:
                self.count += 1
                return self.count
            raise StopIteration

    assert list(ASyncObjectWithIter()) == [1, 2, 3]


class ClassWithGenFunc(ASyncGenericBase):
    async def generate(self):
        yield 0
        yield 1
        yield 2


def test_bound_generator_meta_sync():
    """Does the metaclass handle generator functions correctly?"""
    for _ in ClassWithGenFunc().generate():
        assert isinstance(_, int)


@pytest.mark.asyncio_cooperative
async def test_bound_generator_meta_async():
    """Does the metaclass handle generator functions correctly?"""
    async for _ in ClassWithGenFunc().generate():
        assert isinstance(_, int)
