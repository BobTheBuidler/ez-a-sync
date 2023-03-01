
import pytest
from time import time
from tests.fixtures import TestSemaphore, increment


# ISSUES
# - We are unable to pass in an existing semaphore object, it attaches to a different loop.
#   Maybe a problem with test suite interaction?
# - semaphore modifier works fine with integer inputs

@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore(i: int):
    instance = TestSemaphore(i, sync=False)
    
    start = time()
    assert await instance.test_fn() == i
    duration = time() - start
    assert i < 3 or duration > i # There is a 1 second sleep in this fn. If the semaphore is not working, all tests will complete in 1 second.
    
    
@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore_property(i: int):
    instance = TestSemaphore(i, sync=False)
    start = time()
    assert await instance.test_property == i * 2
    duration = time() - start
    assert i < 3 or duration > i # There is a 1 second sleep in this fn. If the semaphore is not working, all tests will complete in 1 second.
    
    
    
@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore_cached_property(i: int):
    instance = TestSemaphore(i, sync=False)
    start = time()
    assert await instance.test_cached_property == i * 3
    duration = time() - start
    # There is a 1 second sleep in this fn but a semaphore override with a value of 50. 
    # You can tell it worked correctly because the class-defined semaphore value is just one, whch would cause this test to fail if it were used.
    # If the override is not working, all tests will complete in just over 1 second.
    assert i < 3 or duration < 1.5 
