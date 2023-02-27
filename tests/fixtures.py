
import asyncio

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
        return self.v
    
    @a_sync.aka.property
    async def test_property(self) -> int:
        return self.v * 2
    
    @a_sync.alias.cached_property
    async def test_cached_property(self) -> int:
        await asyncio.sleep(2)
        return self.v * 3

class TestInheritor(TestClass):
    pass

class TestMeta(TestClass, metaclass=ASyncMeta):
    pass

class TestSingleton(ASyncGenericSingleton, TestClass):
    pass

class TestSingletonMeta(TestClass, metaclass=ASyncSingletonMeta):
    pass
