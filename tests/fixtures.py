
import asyncio

import pytest

from a_sync import ASyncBase, async_cached_property, async_property
from a_sync._meta import ASyncMeta

increment = pytest.mark.parametrize('i', range(10))

class TestClass(ASyncBase):
    def __init__(self, v: int, sync: bool):
        self.v = v
        self.sync = sync
    
    async def test_fn(self) -> int:
        return self.v
    
    @async_property
    async def test_property(self) -> int:
        return self.v * 2
    
    @async_cached_property
    async def test_cached_property(self) -> int:
        await asyncio.sleep(2)
        return self.v * 3

class TestInheritor(TestClass):
    pass

class TestMeta(TestClass, metaclass=ASyncMeta):
    pass
