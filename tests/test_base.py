
import asyncio
import inspect

from tests.fixtures import TestClass
from a_sync._meta import ASyncMeta

def _await(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

def test_base_sync():
    sync_instance = TestClass(True)
    assert isinstance(sync_instance.__class__, ASyncMeta)

    assert sync_instance.test_fn() == 2
    assert sync_instance.test_property == 4
    assert sync_instance.test_cached_property == 6

    # Can we override with kwargs?
    assert inspect.isawaitable(sync_instance.test_fn(sync=False))

def test_base_async():
    async_instance = TestClass(False)
    assert isinstance(async_instance.__class__, ASyncMeta)

    assert _await(async_instance.test_fn()) == 2
    assert _await(async_instance.test_property) == 4
    assert _await(async_instance.test_cached_property) == 6

    # Can we override with kwargs?
    assert isinstance(async_instance.test_fn(sync=True), int)