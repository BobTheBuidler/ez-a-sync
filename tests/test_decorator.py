
import asyncio
import pytest

import a_sync
from tests.fixtures import _test_kwargs



# ASYNC DEF
def test_decorator_no_args():
    @a_sync.a_sync
    async def some_test_fn() -> int:
        return 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    _test_kwargs(some_test_fn, None)
    
    @a_sync.a_sync()
    async def some_test_fn() -> int:
        return 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    _test_kwargs(some_test_fn, None)
    
def test_decorator_default_none_arg():
    @a_sync.a_sync(None)
    async def some_test_fn() -> int:
        return 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    _test_kwargs(some_test_fn, None)
    
def test_decorator_default_none_kwarg():
    @a_sync.a_sync(default=None)
    async def some_test_fn() -> int:
        return 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    _test_kwargs(some_test_fn, None)

def test_decorator_default_sync_arg():
    @a_sync.a_sync('sync')
    async def some_test_fn() -> int:
        return 2
    with pytest.raises(TypeError):
        asyncio.get_event_loop().run_until_complete(some_test_fn())
    assert some_test_fn() == 2
    _test_kwargs(some_test_fn, 'sync')

def test_decorator_default_sync_kwarg():
    @a_sync.a_sync(default='sync')
    async def some_test_fn() -> int:
        return 2
    with pytest.raises(TypeError):
        asyncio.get_event_loop().run_until_complete(some_test_fn())
    assert some_test_fn() == 2
    _test_kwargs(some_test_fn, 'sync')
    
def test_decorator_default_async_arg():
    @a_sync.a_sync('async')
    async def some_test_fn() -> int:
        return 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    _test_kwargs(some_test_fn, 'async')
    
def test_decorator_default_async_kwarg():
    @a_sync.a_sync(default='async')
    async def some_test_fn() -> int:
        return 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    _test_kwargs(some_test_fn, 'async')


# SYNC DEF
def test_sync_decorator_no_args():
    @a_sync.a_sync
    def some_test_fn() -> int:
        return 2
    assert some_test_fn() == 2
    _test_kwargs(some_test_fn, None)
    
    @a_sync.a_sync()
    def some_test_fn() -> int:
        return 2
    assert some_test_fn() == 2
    _test_kwargs(some_test_fn, None)
    
def test_sync_decorator_default_none_arg():
    @a_sync.a_sync(None)
    def some_test_fn() -> int:
        return 2
    assert some_test_fn() == 2
    _test_kwargs(some_test_fn, None)
    
def test_sync_decorator_default_none_kwarg():
    @a_sync.a_sync(default=None)
    def some_test_fn() -> int:
        return 2
    assert some_test_fn() == 2
    _test_kwargs(some_test_fn, None)

def test_sync_decorator_default_sync_arg():
    @a_sync.a_sync('sync')
    def some_test_fn() -> int:
        return 2
    assert some_test_fn() == 2
    _test_kwargs(some_test_fn, 'sync')

def test_sync_decorator_default_sync_kwarg():
    @a_sync.a_sync(default='sync')
    def some_test_fn() -> int:
        return 2
    assert some_test_fn() == 2
    _test_kwargs(some_test_fn, 'sync')
    
def test_sync_decorator_default_async_arg():
    @a_sync.a_sync('async')
    def some_test_fn() -> int:
        return 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    _test_kwargs(some_test_fn, 'async')
    
def test_sync_decorator_default_async_kwarg():
    @a_sync.a_sync(default='async')
    def some_test_fn() -> int:
        return 2
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    _test_kwargs(some_test_fn, 'async')
