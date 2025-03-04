import pytest
import asyncio
import sys
from time import time

from a_sync.primitives.locks.semaphore import Semaphore
from tests.fixtures import TestSemaphore, increment


# ISSUES
# - We are unable to pass in an existing semaphore object, it attaches to a different loop.
#   Maybe a problem with test suite interaction?
# - semaphore modifier works fine with integer inputs


instance = TestSemaphore(1, sync=False)


def test_semaphore_init():
    assert Semaphore(1)._value == Semaphore()._value == 1
    repr(Semaphore(1))


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


@pytest.mark.asyncio_cooperative
async def test_semaphore_acquire_release():
    semaphore = Semaphore(2)
    await semaphore.acquire()
    assert semaphore._value == 1
    semaphore.release()
    assert semaphore._value == 2


@pytest.mark.asyncio_cooperative
async def test_semaphore_blocking():
    semaphore = Semaphore(1)

    async def task():
        await semaphore.acquire()
        await asyncio.sleep(0.1)
        semaphore.release()

    await semaphore.acquire()
    task1 = asyncio.create_task(task())
    await asyncio.sleep(0.05)
    assert semaphore.locked()
    semaphore.release()
    await task1


@pytest.mark.asyncio_cooperative
async def test_semaphore_multiple_tasks():
    semaphore = Semaphore(2)
    results = []

    async def task(index):
        await semaphore.acquire()
        results.append(index)
        await asyncio.sleep(0.1)
        semaphore.release()

    tasks = [asyncio.create_task(task(i)) for i in range(4)]
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2, 3]


@pytest.mark.asyncio_cooperative
async def test_semaphore_with_zero_initial_value():
    semaphore = Semaphore(0)

    async def task():
        await semaphore.acquire()
        return "done"

    task1 = asyncio.create_task(task())
    await asyncio.sleep(0.1)
    assert not task1.done()
    semaphore.release()
    result = await task1
    assert result == "done"


def test_semaphore_negative_initial_value():
    with pytest.raises(ValueError):
        Semaphore(-1)
    with pytest.raises(TypeError):
        Semaphore(None)
    with pytest.raises(TypeError):
        Semaphore("None")


@pytest.mark.asyncio_cooperative
async def test_semaphore_releasing_without_acquiring():
    semaphore = Semaphore(1)
    semaphore.release()
    assert semaphore._value == 2


"""
@pytest.mark.asyncio_cooperative
async def test_semaphore_with_custom_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    semaphore = Semaphore(1)

    async def task():
        await semaphore.acquire()
        return 'done'

    task1 = loop.create_task(task())
    loop.call_soon(semaphore.release)
    result = loop.run_until_complete(task1)
    assert result == 'done'
    loop.close()
"""


@pytest.mark.asyncio_cooperative
async def test_concurrent_acquire_release():
    semaphore = Semaphore(2)
    results = []

    async def task(index):
        await semaphore.acquire()
        results.append(index)
        await asyncio.sleep(0.1)
        semaphore.release()

    tasks = [asyncio.create_task(task(i)) for i in range(10)]
    await asyncio.gather(*tasks)
    assert sorted(results) == list(range(10))


@pytest.mark.asyncio_cooperative
async def test_semaphore_max_integer_value():
    semaphore = Semaphore(sys.maxsize)
    await semaphore.acquire()
    assert semaphore._value == sys.maxsize - 1
    semaphore.release()
    assert semaphore._value == sys.maxsize


@pytest.mark.asyncio_cooperative
async def test_rapid_acquire_release():
    semaphore = Semaphore(1)

    async def task():
        for _ in range(100):
            await semaphore.acquire()
            semaphore.release()

    await asyncio.gather(*(task() for _ in range(10)))


@pytest.mark.asyncio_cooperative
async def test_exception_handling_during_acquire():
    semaphore = Semaphore(1)

    async def task():
        try:
            await semaphore.acquire()
            raise ValueError("Intentional error")
        except ValueError:
            semaphore.release()

    await task()
    assert semaphore._value == 1


@pytest.mark.asyncio_cooperative
async def test_cancelled_acquire():
    semaphore = Semaphore(1)

    async def task():
        await semaphore.acquire()
        await asyncio.sleep(0.5)
        semaphore.release()

    task1 = asyncio.create_task(task())
    await asyncio.sleep(0.1)

    async def waiting_task():
        await semaphore.acquire()

    waiting_task1 = asyncio.create_task(waiting_task())
    await asyncio.sleep(0.1)
    waiting_task1.cancel()
    await task1


@pytest.mark.asyncio_cooperative
async def test_delayed_release():
    semaphore = Semaphore(1)

    async def task():
        await semaphore.acquire()
        await asyncio.sleep(1)
        semaphore.release()

    task1 = asyncio.create_task(task())
    await asyncio.sleep(0.1)
    assert semaphore.locked()
    await task1


@pytest.mark.asyncio_cooperative
async def test_invalid_release():
    semaphore = Semaphore(1)
    semaphore.release()
    semaphore.release()
    assert semaphore._value == 3


@pytest.mark.asyncio_cooperative
async def test_custom_error_handling():
    semaphore = Semaphore(1)

    async def task():
        try:
            await semaphore.acquire()
            raise RuntimeError("Custom error")
        except RuntimeError:
            semaphore.release()

    await task()
    assert semaphore._value == 1


@pytest.mark.asyncio_cooperative
async def test_dynamic_resizing():
    semaphore = Semaphore(2)
    semaphore._value = 5
    await semaphore.acquire()
    assert semaphore._value == 4
    semaphore.release()
    assert semaphore._value == 5


@pytest.mark.asyncio_cooperative
async def test_high_frequency_operations():
    semaphore = Semaphore(1)

    async def task():
        for _ in range(1000):
            await semaphore.acquire()
            semaphore.release()

    await asyncio.gather(*(task() for _ in range(10)))


@pytest.mark.asyncio_cooperative
async def test_semaphore_as_context_manager():
    semaphore = Semaphore(1)

    async def task():
        async with semaphore:
            assert semaphore._value == 0

    await task()
    assert semaphore._value == 1


@pytest.mark.asyncio_cooperative
async def test_exception_in_release():
    semaphore = Semaphore(1)

    async def task():
        await semaphore.acquire()
        try:
            raise RuntimeError("Error during release")
        finally:
            semaphore.release()

    with pytest.raises(RuntimeError):
        await task()

    assert semaphore._value == 1


"""
@pytest.mark.asyncio_cooperative
async def test_external_interruptions():
    semaphore = Semaphore(1)

    async def task():
        await semaphore.acquire()
        await asyncio.sleep(0.1)
        semaphore.release()

    task1 = asyncio.create_task(task())
    await asyncio.sleep(0.05)
    task1.cancel()
    await asyncio.sleep(0.1)
    assert semaphore._value == 1
"""
