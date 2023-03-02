
import asyncio
import time

import pytest

from a_sync._meta import ASyncMeta
from tests.fixtures import TestClass, TestInheritor, TestMeta, increment, TestSync

classes = pytest.mark.parametrize('cls', [TestClass, TestSync, TestInheritor, TestMeta])

@classes
@increment
def test_base_sync(cls: type, i: int):
    sync_instance = cls(i, True)
    assert isinstance(sync_instance.__class__, ASyncMeta)

    assert sync_instance.test_fn() == i
    assert sync_instance.test_property == i * 2
    start = time.time()
    assert sync_instance.test_cached_property == i * 3
    assert isinstance(sync_instance.test_cached_property, int)
    duration = time.time() - start
    assert duration < 3, "There is a 2 second sleep in 'test_cached_property' but it should only run once."

    # Can we override with kwargs?
    val = asyncio.get_event_loop().run_until_complete(sync_instance.test_fn(sync=False))
    assert isinstance(val, int)

    # Can we access hidden methods for properties?
    assert sync_instance.__test_property__() == i * 2
    start = time.time()
    assert sync_instance.__test_cached_property__() == i * 3
    # Can we override them too?
    assert asyncio.get_event_loop().run_until_complete(sync_instance.__test_cached_property__(sync=False)) == i * 3
    duration = time.time() - start
    assert duration < 3, "There is a 2 second sleep in 'test_cached_property' but it should only run once."

@classes
@increment
@pytest.mark.asyncio_cooperative
async def test_base_async(cls: type, i: int):
    async_instance = cls(i, False)
    assert isinstance(async_instance.__class__, ASyncMeta)
    
    assert await async_instance.test_fn() == i
    assert await async_instance.test_property == i * 2
    start = time.time()
    assert await async_instance.test_cached_property == i * 3
    assert isinstance(await async_instance.test_cached_property, int)
    duration = time.time() - start
    target_duration = 5 if isinstance(async_instance, TestSync) else 3
    # For TestSync, the duration can be higher because the calls execute inside of a threadpool which limits the amount of concurrency.
    assert duration < target_duration, "There is a 2 second sleep in 'test_cached_property' but it should only run once."

    #if isinstance(async_instance, TestSync):
    #    # NOTE this shoudl probbaly run sync in main thread instead of raising...
    #    with pytest.raises(RuntimeError):
    #        await async_instance.test_fn()
        
    # Can we override with kwargs?
    
    if not isinstance(async_instance, TestSync):
        with pytest.raises(RuntimeError):
            async_instance.test_fn(sync=True)
    
    # Can we access hidden methods for properties?
    assert await async_instance.__test_property__() == i * 2
    assert await async_instance.__test_cached_property__() == i * 3
    # Can we override them too?
    with pytest.raises(RuntimeError):
        async_instance.__test_cached_property__(sync=True)
