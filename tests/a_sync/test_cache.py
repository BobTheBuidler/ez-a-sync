import asyncio
from time import sleep, time

import pytest

import a_sync
from tests.fixtures import _test_kwargs


def test_decorator_async_with_cache_type():
    @a_sync.a_sync(default="async", cache_type="memory")
    async def some_test_fn() -> int:
        return 2

    start = time()
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    duration = time() - start
    assert duration < 1.5, "There is a 1 second sleep in this function but it should only run once."
    _test_kwargs(some_test_fn, "async")


def test_decorator_async_with_cache_maxsize():
    @a_sync.a_sync(default="async", ram_cache_maxsize=100)
    def some_test_fn() -> int:
        sleep(1)
        return 2

    start = time()
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    duration = time() - start
    assert duration < 1.5, "There is a 1 second sleep in this function but it should only run once."
    _test_kwargs(some_test_fn, "async")


# This will never succeed due to some task the ttl kwargs creates
def test_decorator_async_with_cache_ttl():
    @a_sync.a_sync(default="async", cache_type="memory", ram_cache_ttl=5)
    async def some_test_fn() -> int:
        return 2

    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    _test_kwargs(some_test_fn, "async")


def test_decorator_sync_with_cache_type():
    # Fails
    @a_sync.a_sync(default="sync", cache_type="memory")
    async def some_test_fn() -> int:
        sleep(1)
        return 2

    start = time()
    assert some_test_fn() == 2
    assert some_test_fn() == 2
    assert some_test_fn() == 2
    duration = time() - start
    assert duration < 1.5, "There is a 1 second sleep in this function but it should only run once."
    _test_kwargs(some_test_fn, "sync")


@pytest.mark.skipif(True, reason="skipped manually")
def test_decorator_sync_with_cache_maxsize():
    # Fails
    # TODO diagnose and fix
    @a_sync.a_sync(default="sync", cache_type="memory")
    def some_test_fn() -> int:
        sleep(1)
        return 2

    start = time()
    assert some_test_fn() == 2
    assert some_test_fn() == 2
    assert some_test_fn() == 2
    duration = time() - start
    assert duration < 1.5, "There is a 1 second sleep in this function but it should only run once."
    _test_kwargs(some_test_fn, "sync")
