
import asyncio
import pytest
import time

from tests.fixtures import TestClass
from a_sync._meta import ASyncMeta


@pytest.mark.parametrize('i', range(10))
def test_base_sync(i: int):
    sync_instance = TestClass(i, True)
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
    assert sync_instance.__test_property() == i * 2
    start = time.time()
    assert sync_instance.__test_cached_property() == i * 3
    # Can we override them too?
    assert asyncio.get_event_loop().run_until_complete(sync_instance.__test_cached_property(sync=False)) == i * 3
    duration = time.time() - start
    assert duration < 3, "There is a 2 second sleep in 'test_cached_property' but it should only run once."

@pytest.mark.asyncio
@pytest.mark.parametrize('i', list(range(10)))
async def test_base_async(i: int):
    async_instance = TestClass(i, False)
    assert isinstance(async_instance.__class__, ASyncMeta)

    assert await async_instance.test_fn() == i
    assert await async_instance.test_property == i * 2
    start = time.time()
    assert await async_instance.test_cached_property == i * 3
    assert isinstance(await async_instance.test_cached_property, int)
    duration = time.time() - start
    assert duration < 3, "There is a 2 second sleep in 'test_cached_property' but it should only run once."

    # Can we override with kwargs?
    with pytest.raises(RuntimeError):
        async_instance.test_fn(sync=True)
    
    # Can we access hidden methods for properties?
    assert await async_instance.__test_property() == i * 2
    assert await async_instance.__test_cached_property() == i * 3
    # Can we override them too?
    with pytest.raises(RuntimeError):
        async_instance.__test_cached_property(sync=True)
