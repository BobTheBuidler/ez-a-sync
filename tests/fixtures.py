
import asyncio
import time
from threading import current_thread, main_thread

import pytest

import a_sync
from a_sync import ASyncBase
from a_sync._meta import ASyncMeta, ASyncSingletonMeta
from a_sync.singleton import ASyncGenericSingleton

increment = pytest.mark.parametrize('i', range(10))

class TestClass(ASyncBase):
    def __init__(self, v: int, sync: bool):
        self.v = v
        self.sync = sync
    
    async def test_fn(self) -> int:
        if self.sync == False:
            assert main_thread() == current_thread(), f'This should be running on an event loop in the main thread.'
        elif self.sync == True:
            assert main_thread() == current_thread(), f'This should be awaited in the main thread'
        return self.v
    
    @a_sync.aka.property
    async def test_property(self) -> int:
        if self.sync == False:
            assert main_thread() == current_thread(), f'This should be running on an event loop in the main thread.'
        elif self.sync == True:
            assert main_thread() == current_thread(), f'This should be awaited in the main thread'
        return self.v * 2
    
    @a_sync.alias.cached_property
    async def test_cached_property(self) -> int:
        if self.sync == False:
            assert main_thread() == current_thread(), f'This should be running on an event loop in the main thread.'
        elif self.sync == True:
            assert main_thread() == current_thread(), f'This should be awaited in the main thread'
        await asyncio.sleep(2)
        return self.v * 3

class TestSync(ASyncBase):
    main = main_thread()
    def __init__(self, v: int, sync: bool):
        self.v = v
        self.sync = sync
    
    def test_fn(self) -> int:
        # Sync bound methods are actually async functions that are run in an executor and awaited
        if self.sync == False:
            assert main_thread() == self.main
            assert main_thread() is not current_thread(), f'This should be running in an executor, not the main thread.'
        elif self.sync == True:
            assert main_thread() is not current_thread(), f'This should be running synchronously in the main thread'
        return self.v
    
    @a_sync.aka.property
    def test_property(self) -> int:
        if self.sync == False:
            assert main_thread() is not current_thread(), f'This should be running in an executor, not the main thread.'
        elif self.sync == True:
            # Sync properties are actually async functions that are run in an executor and awaited
            assert main_thread() is not current_thread(), f'This should be running in an executor, not the main thread.'
        return self.v * 2
    
    @a_sync.alias.cached_property
    def test_cached_property(self) -> int:
        if self.sync == False:
            assert main_thread() is not current_thread(), f'This should be running in an executor, not the main thread.'
        elif self.sync == True:
            # Sync properties are actually async functions that are run in an executor and awaited
            assert main_thread() is not current_thread(), f'This should be running in an executor, not the main thread.'
        time.sleep(2)
        return self.v * 3

class TestInheritor(TestClass):
    pass

class TestMeta(TestClass, metaclass=ASyncMeta):
    pass

class TestSingleton(ASyncGenericSingleton, TestClass):
    runs_per_minute = 100
    pass

class TestSingletonMeta(TestClass, metaclass=ASyncSingletonMeta):
    semaphore = 1
    pass
