"""Tests for limiter functionality in the a_sync module.

This module tests the behavior of the limiter modifier as implemented in the :class:`TestLimiter` fixture.
Note that due to a known limitation, you cannot pass an existing semaphore object into the limiter modifier.
When an already‐created semaphore is provided, it attaches to a different event loop rather than the intended one.
Only integer inputs are supported reliably for the semaphore modifier.

See Also: :class:`ASyncMethodDescriptorSyncDefault`
"""

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
    """Tests that the limiter modifies the executed function's output correctly.

    This test instantiates a :class:`TestLimiter` object with an integer input.
    Note that passing an existing semaphore object is not supported due to event loop issues.
    """
    instance = TestLimiter(i, sync=False)
    assert await instance.test_fn() == i


@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore_property(i: int):
    """Tests that a property modified by the limiter returns the correct computed value.

    This test instantiates a :class:`TestLimiter` object using an integer input.
    Do not attempt to pass in an already‐created semaphore object.
    """
    instance = TestLimiter(i, sync=False)
    assert await instance.test_property == i * 2


@increment
@pytest.mark.asyncio_cooperative
async def test_semaphore_cached_property(i: int):
    """Tests that a cached property modified by the limiter returns the expected result.

    This test creates a :class:`TestLimiter` instance using an integer input.
    Reminder: existing semaphore objects are not supported; only integer values work as intended.
    """
    instance = TestLimiter(i, sync=False)
    assert await instance.test_cached_property == i * 3