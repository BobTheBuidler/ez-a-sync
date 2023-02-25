from a_sync import ASyncBase
from async_property import async_property, async_cached_property

class TestClass(ASyncBase):
    def __init__(self, sync: bool):
        self.sync = sync
    
    async def test_fn(self) -> int:
        return 2
    
    @async_property
    async def test_property(self) -> int:
        return 4
    
    @async_cached_property
    async def test_cached_property(self) -> int:
        return 6
    