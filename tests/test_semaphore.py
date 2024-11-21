import pytest
from time import time

from a_sync import Semaphore
from tests.fixtures import TestSemaphore, increment


# ISSUES
# - We are unable to pass in an existing semaphore object, it attaches to a different loop.
#   Maybe a problem with test suite interaction?
# - semaphore modifier works fine with integer inputs


instance = TestSemaphore(1, sync=False)


def test_semaphore_init():
    assert Semaphore(1)._value == Semaphore()._value == 1


@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore(i: int):
    start = time()
    assert await instance.test_fn() == 1
    duration = time() - start
    # There is a 1 second sleep in this fn. If the semaphore is not working, all tests will complete in 1 second.
    assert i < 3 or duration > i 


@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore_property(i: int):
    start = time()
    assert await instance.test_property == 2
    duration = time() - start
    # There is a 1 second sleep in this fn. If the semaphore is not working, all tests will complete in 1 second.
    assert i < 3 or duration > i 


@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore_cached_property(i: int):
    start = time()
    assert await instance.test_cached_property == 3
    duration = time() - start
    # There is a 1 second sleep in this fn but a semaphore override with a value of 50.
    # You can tell it worked correctly because the class-defined semaphore value is just one, whch would cause this test to fail if it were used.
    # If the override is not working, all tests will complete in just over 1 second.
    # We increased the threshold from 1.05 to 1.4 to help tests pass on slow github runners
    assert i == 1 or duration < 1.4
