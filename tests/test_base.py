
import asyncio
import inspect

from tests.fixtures import TestClass

def _await(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

def test_base_sync():
    sync_instance = TestClass(True)
    assert sync_instance.test_fn() == 2
    assert sync_instance.test_property == 4
    assert sync_instance.test_cached_property == 6

    # Can we override with kwargs?
    assert inspect.isawaitable(sync_instance.test_fn(sync=False))

def test_base_async():
    async_instance = TestClass(False)
    assert _await(async_instance.test_fn()) == 2
    assert _await(async_instance.test_property) == 4
    assert _await(async_instance.test_cached_property) == 6

    # Can we override with kwargs?
    assert isinstance(async_instance.test_fn(sync=True), int)