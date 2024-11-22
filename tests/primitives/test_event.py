import pytest
import asyncio
from a_sync.primitives import Event


@pytest.mark.asyncio_cooperative
async def test_event_basic_functionality():
    event = Event()
    assert not event.is_set()
    event.set()
    assert event.is_set()
    event.clear()
    assert not event.is_set()


@pytest.mark.asyncio_cooperative
async def test_event_wait():
    event = Event()

    async def waiter():
        await event.wait()
        return "done"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.1)  # Ensure the waiter is waiting
    event.set()
    result = await waiter_task
    assert result == "done"


@pytest.mark.asyncio_cooperative
async def test_event_multiple_waiters():
    event = Event()
    results = []

    async def waiter(index):
        await event.wait()
        results.append(index)

    tasks = [asyncio.create_task(waiter(i)) for i in range(5)]
    await asyncio.sleep(0.1)  # Ensure all waiters are waiting
    event.set()
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2, 3, 4]


@pytest.mark.asyncio_cooperative
async def test_event_reset():
    event = Event()
    event.set()
    assert event.is_set()
    event.clear()
    assert not event.is_set()

    async def waiter():
        await event.wait()
        return "done"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.1)  # Ensure the waiter is waiting
    event.set()
    result = await waiter_task
    assert result == "done"


@pytest.mark.asyncio_cooperative
async def test_event_timeout():
    event = Event()

    async def waiter():
        try:
            await asyncio.wait_for(event.wait(), timeout=0.1)
        except asyncio.TimeoutError:
            return "timeout"

    result = await waiter()
    assert result == "timeout"


@pytest.mark.asyncio_cooperative
async def test_event_cancellation():
    event = Event()

    async def waiter():
        try:
            await event.wait()
        except asyncio.CancelledError:
            return "cancelled"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.1)  # Ensure the waiter is waiting
    waiter_task.cancel()
    result = await waiter_task
    assert result == "cancelled"


@pytest.mark.asyncio_cooperative
async def test_event_set_already_set():
    event = Event()
    event.set()
    assert event.is_set()
    event.set()  # Set again, should have no adverse effect
    assert event.is_set()


@pytest.mark.asyncio_cooperative
async def test_event_clear_already_cleared():
    event = Event()
    event.clear()  # Clear when already cleared, should have no adverse effect
    assert not event.is_set()


@pytest.mark.asyncio_cooperative
async def test_event_wait_after_set():
    event = Event()
    event.set()

    async def waiter():
        return await event.wait()

    result = await waiter()
    assert result is True


@pytest.mark.asyncio_cooperative
async def test_event_wait_after_clear():
    event = Event()
    event.set()
    event.clear()

    async def waiter():
        try:
            await asyncio.wait_for(event.wait(), timeout=0.1)
        except asyncio.TimeoutError:
            return "timeout"

    result = await waiter()
    assert result == "timeout"


@pytest.mark.asyncio_cooperative
async def test_simultaneous_set_and_wait():
    event = Event()
    results = []

    async def waiter(index):
        await event.wait()
        results.append(index)

    tasks = [asyncio.create_task(waiter(i)) for i in range(5)]
    event.set()
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2, 3, 4]


@pytest.mark.asyncio_cooperative
async def test_reentrant_set():
    event = Event()
    event.set()
    event.set()  # Reentrant set
    assert event.is_set()


@pytest.mark.asyncio_cooperative
async def test_large_number_of_waiters():
    event = Event()
    num_waiters = 1000
    results = []

    async def waiter(index):
        await event.wait()
        results.append(index)

    tasks = [asyncio.create_task(waiter(i)) for i in range(num_waiters)]
    event.set()
    await asyncio.gather(*tasks)
    assert results == list(range(num_waiters))


@pytest.mark.asyncio_cooperative
async def test_event_with_no_waiters():
    event = Event()
    event.set()
    event.clear()
    assert not event.is_set()


@pytest.mark.asyncio_cooperative
async def test_immediate_set_and_wait():
    event = Event()
    event.set()

    async def waiter():
        return await event.wait()

    result = await waiter()
    assert result is True


@pytest.mark.asyncio_cooperative
async def test_event_with_exception_handling():
    event = Event()

    async def waiter():
        try:
            await event.wait()
            raise ValueError("Intentional error")
        except ValueError as e:
            return str(e)

    event.set()
    result = await waiter()
    assert result == "Intentional error"


@pytest.mark.asyncio_cooperative
async def test_event_with_loop_reentrancy():
    event = Event()

    async def loop_task():
        for _ in range(3):
            event.set()
            await event.wait()
            event.clear()

    await loop_task()


@pytest.mark.asyncio_cooperative
async def test_event_with_delayed_set():
    event = Event()

    async def waiter():
        await event.wait()
        return "done"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.5)  # Delay before setting the event
    event.set()
    result = await waiter_task
    assert result == "done"


@pytest.mark.asyncio_cooperative
async def test_event_with_multiple_clears():
    event = Event()
    event.clear()
    event.clear()  # Multiple clears
    assert not event.is_set()
