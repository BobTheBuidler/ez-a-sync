import asyncio
import sys
from collections.abc import Callable
from time import time
from typing import Any, TypeVar, cast

import pytest

from a_sync.primitives.locks.semaphore import Semaphore
from tests.fixtures import TestSemaphore, increment

# ISSUES
# - We are unable to pass in an existing semaphore object, it attaches to a different loop.
#   Maybe a problem with test suite interaction?
# - semaphore modifier works fine with integer inputs

_F = TypeVar("_F", bound=Callable[..., Any])
asyncio_cooperative = cast(Callable[[_F], _F], pytest.mark.asyncio_cooperative)
increment = cast(Callable[[_F], _F], increment)

instance = TestSemaphore(1, sync=False)


def test_semaphore_init() -> None:
    assert Semaphore(1)._value == Semaphore()._value == 1
    repr(Semaphore(1))


@increment
@asyncio_cooperative
async def test_semaphore(i: int) -> None:
    start = time()
    assert await instance.test_fn() == 1
    duration = time() - start
    # There is a 1 second sleep in this fn. If the semaphore is not working, all tests will complete in 1 second.
    assert i < 3 or duration > i


@increment
@asyncio_cooperative
async def test_semaphore_property(i: int) -> None:
    start = time()
    assert await instance.test_property == 2
    duration = time() - start
    # There is a 1 second sleep in this fn. If the semaphore is not working, all tests will complete in 1 second.
    assert i < 3 or duration > i


@increment
@asyncio_cooperative
async def test_semaphore_cached_property(i: int) -> None:
    start = time()
    assert await instance.test_cached_property == 3
    duration = time() - start
    # There is a 1 second sleep in this fn but a semaphore override with a value of 50.
    # You can tell it worked correctly because the class-defined semaphore value is just one, whch would cause this test to fail if it were used.
    # If the override is not working, all tests will complete in just over 1 second.
    # We increased the threshold from 1.05 to 1.4 to help tests pass on slow github runners
    assert i == 1 or duration < 1.4


@asyncio_cooperative
async def test_semaphore_acquire_release() -> None:
    semaphore = Semaphore(2)
    await semaphore.acquire()
    assert semaphore._value == 1
    semaphore.release()
    assert semaphore._value == 2


@asyncio_cooperative
async def test_semaphore_blocking() -> None:
    semaphore = Semaphore(1)

    async def task() -> None:
        await semaphore.acquire()
        await asyncio.sleep(0.1)
        semaphore.release()

    await semaphore.acquire()
    task1 = asyncio.create_task(task())
    await asyncio.sleep(0.05)
    assert semaphore.locked()
    semaphore.release()
    await task1


@asyncio_cooperative
async def test_semaphore_multiple_tasks() -> None:
    semaphore = Semaphore(2)
    results: list[int] = []

    async def task(index: int) -> None:
        await semaphore.acquire()
        results.append(index)
        await asyncio.sleep(0.1)
        semaphore.release()

    tasks = [asyncio.create_task(task(i)) for i in range(4)]
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2, 3]


@asyncio_cooperative
async def test_semaphore_with_zero_initial_value() -> None:
    semaphore = Semaphore(0)

    async def task() -> str:
        await semaphore.acquire()
        return "done"

    task1 = asyncio.create_task(task())
    await asyncio.sleep(0.1)
    assert not task1.done()
    semaphore.release()
    result = await task1
    assert result == "done"


def test_semaphore_negative_initial_value() -> None:
    with pytest.raises(ValueError):
        Semaphore(-1)
    with pytest.raises(TypeError):
        Semaphore(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Semaphore("None")  # type: ignore[arg-type]


@asyncio_cooperative
async def test_semaphore_releasing_without_acquiring() -> None:
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


@asyncio_cooperative
async def test_concurrent_acquire_release() -> None:
    semaphore = Semaphore(2)
    results: list[int] = []

    async def task(index: int) -> None:
        await semaphore.acquire()
        results.append(index)
        await asyncio.sleep(0.1)
        semaphore.release()

    tasks = [asyncio.create_task(task(i)) for i in range(10)]
    await asyncio.gather(*tasks)
    assert sorted(results) == list(range(10))


@asyncio_cooperative
async def test_semaphore_max_integer_value() -> None:
    semaphore = Semaphore(sys.maxsize)
    await semaphore.acquire()
    assert semaphore._value == sys.maxsize - 1
    semaphore.release()
    assert semaphore._value == sys.maxsize


@asyncio_cooperative
async def test_rapid_acquire_release() -> None:
    semaphore = Semaphore(1)

    async def task() -> None:
        for _ in range(100):
            await semaphore.acquire()
            semaphore.release()

    await asyncio.gather(*(task() for _ in range(10)))


@asyncio_cooperative
async def test_exception_handling_during_acquire() -> None:
    semaphore = Semaphore(1)

    async def task() -> None:
        try:
            await semaphore.acquire()
            raise ValueError("Intentional error")
        except ValueError:
            semaphore.release()

    await task()
    assert semaphore._value == 1


@asyncio_cooperative
async def test_cancelled_acquire() -> None:
    semaphore = Semaphore(1)

    async def task() -> None:
        await semaphore.acquire()
        await asyncio.sleep(0.5)
        semaphore.release()

    task1 = asyncio.create_task(task())
    await asyncio.sleep(0.1)

    async def waiting_task() -> None:
        await semaphore.acquire()

    waiting_task1 = asyncio.create_task(waiting_task())
    await asyncio.sleep(0.1)
    waiting_task1.cancel()
    await task1


@asyncio_cooperative
async def test_delayed_release() -> None:
    semaphore = Semaphore(1)

    async def task() -> None:
        await semaphore.acquire()
        await asyncio.sleep(1)
        semaphore.release()

    task1 = asyncio.create_task(task())
    await asyncio.sleep(0.1)
    assert semaphore.locked()
    await task1


@asyncio_cooperative
async def test_invalid_release() -> None:
    semaphore = Semaphore(1)
    semaphore.release()
    semaphore.release()
    assert semaphore._value == 3


@asyncio_cooperative
async def test_custom_error_handling() -> None:
    semaphore = Semaphore(1)

    async def task() -> None:
        try:
            await semaphore.acquire()
            raise RuntimeError("Custom error")
        except RuntimeError:
            semaphore.release()

    await task()
    assert semaphore._value == 1


@asyncio_cooperative
async def test_dynamic_resizing() -> None:
    semaphore = Semaphore(2)
    semaphore._value = 5
    await semaphore.acquire()
    assert semaphore._value == 4
    semaphore.release()
    assert semaphore._value == 5


@asyncio_cooperative
async def test_high_frequency_operations() -> None:
    semaphore = Semaphore(1)

    async def task() -> None:
        for _ in range(1000):
            await semaphore.acquire()
            semaphore.release()

    await asyncio.gather(*(task() for _ in range(10)))


@asyncio_cooperative
async def test_semaphore_as_context_manager() -> None:
    semaphore = Semaphore(1)

    async def task() -> None:
        async with semaphore:
            assert semaphore._value == 0

    await task()
    assert semaphore._value == 1


@asyncio_cooperative
async def test_exception_in_release() -> None:
    semaphore = Semaphore(1)

    async def task() -> None:
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
