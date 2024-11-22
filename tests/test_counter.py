import pytest
from a_sync.primitives import CounterLock

@pytest.mark.asyncio_cooperative
async def test_counter_lock():
    assert await CounterLock().wait_for(0)