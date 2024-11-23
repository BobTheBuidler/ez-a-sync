import pytest
from time import time
from tests.fixtures import TestLimiter, increment


# ISSUES
# - We are unable to pass in an existing semaphore object, it attaches to a different loop.
#   Maybe a problem with test suite interaction?
# - semaphore modifier works fine with integer inputs


@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore(i: int):
    instance = TestLimiter(i, sync=False)
    assert await instance.test_fn() == i


@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore_property(i: int):
    instance = TestLimiter(i, sync=False)
    assert await instance.test_property == i * 2


@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore_cached_property(i: int):
    instance = TestLimiter(i, sync=False)
    assert await instance.test_cached_property == i * 3
