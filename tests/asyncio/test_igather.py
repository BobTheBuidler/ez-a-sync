import pytest

from a_sync import igather
from a_sync.asyncio import sleep0


@pytest.mark.asyncio_cooperative
async def test_igather():
    assert await igather(sleep0() for _ in range(10)) == [None] * 10
