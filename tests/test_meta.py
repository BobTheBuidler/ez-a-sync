import asyncio
import time

import pytest

from a_sync._meta import ASyncMeta
from a_sync.base import ASyncGenericBase
from a_sync.singleton import ASyncGenericSingleton
from tests.fixtures import TestSingleton, TestSingletonMeta, increment

classes = pytest.mark.parametrize('cls', [TestSingleton, TestSingletonMeta])

@classes
@increment
def test_singleton_meta_sync(cls: type, i: int):
    sync_instance = cls(i, sync=True)
    assert isinstance(sync_instance, ASyncGenericBase)
    assert isinstance(sync_instance.__class__, ASyncMeta)

    assert sync_instance.test_fn() == 0
    assert sync_instance.test_property == 0
    start = time.time()
    assert sync_instance.test_cached_property == 0
    assert isinstance(sync_instance.test_cached_property, int)
    duration = time.time() - start
    assert duration < 3, "There is a 2 second sleep in 'test_cached_property' but it should only run once."

    # Can we override with kwargs?
    val = asyncio.get_event_loop().run_until_complete(sync_instance.test_fn(sync=False))
    assert isinstance(val, int)

    # Can we access hidden methods for properties?
    assert sync_instance.__test_property__() == 0
    start = time.time()
    assert sync_instance.__test_cached_property__() == 0
    # Can we override them too?
    assert asyncio.get_event_loop().run_until_complete(sync_instance.__test_cached_property__(sync=False)) == 0
    duration = time.time() - start
    assert duration < 3, "There is a 2 second sleep in 'test_cached_property' but it should only run once."

@classes
@increment
@pytest.mark.asyncio_cooperative
async def test_singleton_meta_async(cls: type, i: int):
    async_instance = cls(i, sync=False)
    assert isinstance(async_instance, ASyncGenericBase)
    assert isinstance(async_instance.__class__, ASyncMeta)

    assert await async_instance.test_fn() == 0
    assert await async_instance.test_property == 0
    start = time.time()
    assert await async_instance.test_cached_property == 0
    assert isinstance(await async_instance.test_cached_property, int)
    duration = time.time() - start
    assert duration < 3, "There is a 2 second sleep in 'test_cached_property' but it should only run once."

    # Can we override with kwargs?
    with pytest.raises(RuntimeError):
        async_instance.test_fn(sync=True)
    
    # Can we access hidden methods for properties?
    assert await async_instance.__test_property__() == 0
    assert await async_instance.__test_cached_property__() == 0
    # Can we override them too?
    with pytest.raises(RuntimeError):
        async_instance.__test_cached_property__(sync=True)



class TestUnspecified(ASyncGenericSingleton):
    def __init__(self, sync=True):
        self.sync = sync

def test_singleton_unspecified():
    obj = TestUnspecified()
    assert obj.sync == True
    obj.test_attr = True
    newobj = TestUnspecified()
    assert hasattr(newobj, 'test_attr')

    assert TestUnspecified(sync=True).sync == True
    assert TestUnspecified(sync=False).sync == False

def test_singleton_switching():
    obj = TestUnspecified()
    assert obj.sync == True
    obj.test_attr = True
    newobj = TestUnspecified(sync=False)
    assert not hasattr(newobj, 'test_attr')