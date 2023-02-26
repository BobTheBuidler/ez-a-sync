
import asyncio

from a_sync import ASyncBase, async_property, async_cached_property

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
    