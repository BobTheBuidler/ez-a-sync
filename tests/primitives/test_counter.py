import asyncio
import pytest
from a_sync.primitives import CounterLock


@pytest.mark.asyncio_cooperative
async def test_counter_lock():
    counter = CounterLock()
    assert counter._name == ""
    assert repr(counter) == "<CounterLock value=0 waiters={}>"
    coro = counter.wait_for(1)
    task = asyncio.create_task(coro)
    await asyncio.sleep(0)
    assert repr(counter) == "<CounterLock value=0 waiters={1: 1}>"
    counter.set(1)
    await asyncio.sleep(0)
    assert task.done() and task.result() is True
    assert repr(counter) == "<CounterLock value=1 waiters={}>"


@pytest.mark.asyncio_cooperative
async def test_counter_lock_with_name():
    counter = CounterLock(name="test")
    assert counter._name == "test"
    assert repr(counter) == "<CounterLock name=test value=0 waiters={}>"
    coro = counter.wait_for(1)
    task = asyncio.create_task(coro)
    await asyncio.sleep(0)
    assert repr(counter) == "<CounterLock name=test value=0 waiters={1: 1}>"
    counter.set(1)
    await asyncio.sleep(0)
    assert task.done() and task.result() is True
    assert repr(counter) == "<CounterLock name=test value=1 waiters={}>"


@pytest.mark.asyncio_cooperative
async def test_counterlock_initialization():
    counter = CounterLock(start_value=5)
    assert counter.value == 5


@pytest.mark.asyncio_cooperative
async def test_counterlock_set():
    counter = CounterLock(start_value=0)
    counter.set(10)
    assert counter.value == 10


@pytest.mark.asyncio_cooperative
async def test_counterlock_wait_for():
    counter = CounterLock(start_value=0)

    async def waiter():
        await counter.wait_for(5)
        return "done"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.1)
    counter.set(5)
    result = await waiter_task
    assert result == "done"


@pytest.mark.asyncio_cooperative
async def test_counterlock_concurrent_waiters():
    counter = CounterLock(start_value=0)
    results = []

    async def waiter(index):
        await counter.wait_for(5)
        results.append(index)

    tasks = [asyncio.create_task(waiter(i)) for i in range(3)]
    await asyncio.sleep(0.1)
    counter.set(5)
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2]


@pytest.mark.asyncio_cooperative
async def test_counterlock_increment_only():
    counter = CounterLock(start_value=5)
    with pytest.raises(ValueError):
        counter.set(3)


@pytest.mark.asyncio_cooperative
async def test_counterlock_large_value():
    counter = CounterLock(start_value=0)
    large_value = 10**6
    counter.set(large_value)
    assert counter.value == large_value


@pytest.mark.asyncio_cooperative
async def test_counterlock_zero_value():
    counter = CounterLock(start_value=0)
    assert counter.value == 0


@pytest.mark.asyncio_cooperative
async def test_counterlock_exception_handling():
    counter = CounterLock(start_value=0)

    async def waiter():
        try:
            await counter.wait_for(5)
            raise ValueError("Intentional error")
        except ValueError as e:
            return str(e)

    counter.set(5)
    result = await waiter()
    assert result == "Intentional error"


@pytest.mark.asyncio_cooperative
async def test_simultaneous_set_and_wait():
    counter = CounterLock(start_value=0)
    results = []

    async def waiter(index):
        await counter.wait_for(5)
        results.append(index)

    tasks = [asyncio.create_task(waiter(i)) for i in range(5)]
    counter.set(5)
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2, 3, 4]


@pytest.mark.asyncio_cooperative
async def test_reentrant_set():
    counter = CounterLock(start_value=0)
    counter.set(5)
    counter.set(10)  # Reentrant set
    assert counter.value == 10


def test_counterlock_invalid_start_value():
    with pytest.raises(TypeError):
        CounterLock(None)


@pytest.mark.asyncio_cooperative
async def test_immediate_set_and_wait():
    counter = CounterLock(start_value=5)

    async def waiter():
        return await counter.wait_for(5)

    result = await waiter()
    assert result is True


@pytest.mark.asyncio_cooperative
async def test_delayed_set():
    counter = CounterLock(start_value=0)

    async def waiter():
        await counter.wait_for(5)
        return "done"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.5)  # Delay before setting the counter
    counter.set(5)
    result = await waiter_task
    assert result == "done"


@pytest.mark.asyncio_cooperative
async def test_multiple_sets():
    counter = CounterLock(start_value=0)
    results = []

    async def waiter(index):
        await counter.wait_for(10)
        results.append(index)

    tasks = [asyncio.create_task(waiter(i)) for i in range(3)]
    counter.set(5)
    counter.set(10)
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2]


@pytest.mark.asyncio_cooperative
async def test_custom_error_handling():
    counter = CounterLock(start_value=0)

    async def waiter():
        try:
            await counter.wait_for(5)
            raise RuntimeError("Custom error")
        except RuntimeError as e:
            return str(e)

    counter.set(5)
    result = await waiter()
    assert result == "Custom error"


@pytest.mark.asyncio_cooperative
async def test_external_interruptions():
    counter = CounterLock(start_value=0)

    async def waiter():
        await counter.wait_for(5)
        return "done"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.1)
    waiter_task.cancel()
    await asyncio.sleep(0.1)
    assert counter.value == 0
