import asyncio
from collections.abc import Callable
from typing import Any, TypeVar, cast, override

import pytest

from a_sync.primitives.queue import (
    PriorityProcessingQueue,
    ProcessingQueue,
    Queue,
    SmartProcessingQueue,
)

_F = TypeVar("_F", bound=Callable[..., Any])
asyncio_cooperative = cast(Callable[[_F], _F], pytest.mark.asyncio_cooperative)


@asyncio_cooperative
async def test_queue_initialization() -> None:
    queue = Queue()
    assert isinstance(queue, Queue)


@asyncio_cooperative
async def test_put_and_get() -> None:
    queue = Queue()
    await queue.put("item1")
    result = await queue.get()
    assert result == "item1"


@asyncio_cooperative
async def test_put_nowait_and_get_nowait() -> None:
    queue = Queue()
    queue.put_nowait("item2")
    result = queue.get_nowait()
    assert result == "item2"

    with pytest.raises(asyncio.QueueEmpty):
        queue.get_nowait()


@asyncio_cooperative
async def test_get_all() -> None:
    queue = Queue()
    await queue.put("item3")
    await queue.put("item4")
    result = await queue.get_all()
    assert result == ["item3", "item4"]


@asyncio_cooperative
async def test_get_all_nowait() -> None:
    queue = Queue()
    queue.put_nowait("item5")
    queue.put_nowait("item6")
    result = queue.get_all_nowait()
    assert result == ["item5", "item6"]

    with pytest.raises(asyncio.QueueEmpty):
        queue.get_all_nowait()


@asyncio_cooperative
async def test_get_multi() -> None:
    queue = Queue()
    await queue.put("item7")
    await queue.put("item8")
    result = await queue.get_multi(2)
    assert result == ["item7", "item8"]


@asyncio_cooperative
async def test_get_multi_nowait() -> None:
    queue = Queue()
    queue.put_nowait("item9")
    queue.put_nowait("item10")
    result = queue.get_multi_nowait(2)
    assert result == ["item9", "item10"]

    with pytest.raises(ValueError, match="`i` must be an integer greater than 1. You passed 1"):
        queue.get_multi_nowait(1)
    with pytest.raises(asyncio.QueueEmpty):
        queue.get_multi_nowait(2)


@asyncio_cooperative
async def test_queue_length() -> None:
    queue = Queue()
    await queue.put("item11")
    assert not queue.empty()
    assert len(queue) == 1
    await queue.get()
    assert len(queue) == 0


@asyncio_cooperative
async def test_concurrent_access() -> None:
    queue = Queue()
    results: list[str] = []

    async def producer() -> None:
        for i in range(5):
            await queue.put(f"item{i}")

    async def consumer() -> None:
        for _ in range(5):
            item = await queue.get()
            results.append(item)

    await asyncio.gather(producer(), consumer())
    assert results == [f"item{i}" for i in range(5)]


@asyncio_cooperative
async def test_empty_queue_behavior() -> None:
    queue: Queue[str] = Queue()

    async def consumer() -> str:
        return cast(str, await queue.get())

    consumer_task = asyncio.create_task(consumer())
    await asyncio.sleep(0.1)  # Ensure the consumer is waiting
    await queue.put("item1")
    result = await consumer_task
    assert result == "item1"


@asyncio_cooperative
async def test_cancellation() -> None:
    queue = Queue()

    async def consumer() -> str | None:
        try:
            await queue.get()
        except asyncio.CancelledError:
            return "cancelled"
        return None

    consumer_task = asyncio.create_task(consumer())
    await asyncio.sleep(0.1)  # Ensure the consumer is waiting
    consumer_task.cancel()
    result = await consumer_task
    assert result == "cancelled"


@asyncio_cooperative
async def test_invalid_get_multi() -> None:
    queue = Queue()
    with pytest.raises(ValueError):
        await queue.get_multi(-1)


@asyncio_cooperative
async def test_type_consistency() -> None:
    queue = Queue()
    await queue.put(1)
    await queue.put("string")
    await queue.put(None)

    assert await queue.get() == 1
    assert await queue.get() == "string"
    assert await queue.get() is None


@asyncio_cooperative
async def test_stress_testing() -> None:
    queue = Queue()
    num_items = 1000

    async def producer() -> None:
        for i in range(num_items):
            await queue.put(f"item{i}")

    async def consumer() -> None:
        for _ in range(num_items):
            await queue.get()

    await asyncio.gather(producer(), consumer())
    assert len(queue) == 0


@asyncio_cooperative
async def test_order_preservation() -> None:
    queue = Queue()
    items = ["item1", "item2", "item3"]
    for item in items:
        await queue.put(item)

    for item in items:
        assert await queue.get() == item


@asyncio_cooperative
async def test_edge_case_values() -> None:
    queue = Queue()
    await queue.put(None)
    await queue.put("")
    await queue.put(" ")

    assert await queue.get() is None
    assert await queue.get() == ""
    assert await queue.get() == " "


@asyncio_cooperative
async def test_timeout_on_get() -> None:
    queue = Queue()

    async def consumer() -> str | None:
        try:
            await asyncio.wait_for(queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return "timeout"
        return None

    result = await consumer()
    assert result == "timeout"


@asyncio_cooperative
async def test_exception_handling_in_callbacks() -> None:
    queue = Queue()

    async def faulty_consumer() -> str:
        try:
            await queue.get()
            raise ValueError("Intentional error")
        except ValueError as e:
            return str(e)

    await queue.put("item")
    result = await faulty_consumer()
    assert result == "Intentional error"


@asyncio_cooperative
async def test_memory_usage() -> None:
    queue = Queue()
    large_object = "x" * 10**6  # 1 MB string
    await queue.put(large_object)
    result = await queue.get()
    assert result == large_object


@asyncio_cooperative
async def test_thread_safety() -> None:
    queue = Queue()

    async def producer() -> None:
        for i in range(5):
            await queue.put(f"item{i}")

    async def consumer() -> list[str]:
        results: list[str] = []
        for _ in range(5):
            item = await queue.get()
            results.append(item)
        return results

    producer_task = asyncio.create_task(producer())
    consumer_task = asyncio.create_task(consumer())
    await asyncio.gather(producer_task, consumer_task)
    assert len(queue) == 0


@asyncio_cooperative
async def test_custom_object_handling() -> None:
    class CustomObject:
        def __init__(self, value: int) -> None:
            self.value = value

        @override
        def __eq__(self, other: object) -> bool:
            if not isinstance(other, CustomObject):
                return False
            return self.value == other.value

    queue = Queue()
    obj1 = CustomObject(1)
    obj2 = CustomObject(2)
    await queue.put(obj1)
    await queue.put(obj2)

    assert await queue.get() == obj1
    assert await queue.get() == obj2


@asyncio_cooperative
async def test_queue_capacity() -> None:
    queue = Queue(maxsize=2)
    await queue.put("item1")
    await queue.put("item2")
    assert queue.full()
    with pytest.raises(asyncio.QueueFull):
        queue.put_nowait("item3")


@asyncio_cooperative
async def test_performance_under_load() -> None:
    queue = Queue()
    num_items = 10000

    async def producer() -> None:
        for i in range(num_items):
            await queue.put(f"item{i}")

    async def consumer() -> None:
        for _ in range(num_items):
            await queue.get()

    await asyncio.gather(producer(), consumer())
    assert len(queue) == 0


@asyncio_cooperative
async def test_state_persistence() -> None:
    queue = Queue()
    await queue.put("item1")
    await queue.put("item2")

    # Simulate state persistence
    state = list(queue._queue)

    # Restore state
    restored_queue = Queue()
    restored_queue._queue.extend(state)

    assert await restored_queue.get() == "item1"
    assert await restored_queue.get() == "item2"


@asyncio_cooperative
async def test_unusual_data_types() -> None:
    queue = Queue()
    await queue.put({"key": "value"})
    await queue.put(["list", "of", "items"])
    await queue.put(("tuple", "of", "items"))

    assert await queue.get() == {"key": "value"}
    assert await queue.get() == ["list", "of", "items"]
    assert await queue.get() == ("tuple", "of", "items")


async def coro_fn(x: str) -> int:
    return int(x)


@asyncio_cooperative
async def test_processing_queue_initialization() -> None:
    queue = ProcessingQueue(coro_fn, 2)
    assert isinstance(queue, ProcessingQueue)
    assert queue.func == coro_fn
    assert queue.num_workers == 2
    assert queue.empty()


@asyncio_cooperative
async def test_processing_put_and_await() -> None:
    queue = ProcessingQueue(coro_fn, 2)
    fut = await queue.put("1")
    assert isinstance(fut, asyncio.Future)
    assert not queue.empty()
    assert await fut == 1
    assert queue.empty()


@asyncio_cooperative
async def test_processing_put_nowait_and_await() -> None:
    queue = ProcessingQueue(coro_fn, 2)
    fut = queue.put_nowait("2")
    assert isinstance(fut, asyncio.Future)
    assert not queue.empty()
    assert await fut == 2
    with pytest.raises(asyncio.QueueEmpty):
        queue.get_nowait()


@asyncio_cooperative
async def test_processing_call() -> None:
    queue = ProcessingQueue(coro_fn, 10)
    big_work = map(queue, map(str, range(100)))
    results = await asyncio.gather(*big_work)
    assert results == list(range(100))
    assert queue.empty()


@asyncio_cooperative
async def test_smart_processing_queue_initialization() -> None:
    queue = SmartProcessingQueue(coro_fn, 2)
    assert isinstance(queue, ProcessingQueue)
    assert queue.func == coro_fn
    assert queue.num_workers == 2
    assert queue.empty()


@asyncio_cooperative
async def test_priority_processing_queue_initialization() -> None:
    queue = PriorityProcessingQueue(coro_fn, 2)
    assert isinstance(queue, PriorityProcessingQueue)
    assert queue.func == coro_fn
    assert queue.num_workers == 2
    assert queue.empty()


@asyncio_cooperative
async def test_smart_processing_put_and_await() -> None:
    queue = SmartProcessingQueue(coro_fn, 2)
    fut = await queue.put("1")
    assert isinstance(fut, asyncio.Future)
    assert not queue.empty()
    assert await fut == 1
    assert queue.empty()


@asyncio_cooperative
async def test_priority_processing_put_and_await() -> None:
    queue = PriorityProcessingQueue(coro_fn, 2)
    fut = await queue.put(5, "1")
    assert isinstance(fut, asyncio.Future)
    assert not queue.empty()
    assert await fut == 1
    assert queue.empty()


@asyncio_cooperative
async def test_smart_processing_put_nowait_and_await() -> None:
    queue = SmartProcessingQueue(coro_fn, 2)
    fut = queue.put_nowait("2")
    assert isinstance(fut, asyncio.Future)
    assert not queue.empty()
    assert await fut == 2
    with pytest.raises(asyncio.QueueEmpty):
        queue.get_nowait()


@asyncio_cooperative
async def test_priority_processing_put_nowait_and_await() -> None:
    queue = PriorityProcessingQueue(coro_fn, 2)
    fut = queue.put_nowait(5, "2")
    assert isinstance(fut, asyncio.Future)
    assert not queue.empty()
    assert await fut == 2
    with pytest.raises(asyncio.QueueEmpty):
        queue.get_nowait()


@asyncio_cooperative
async def test_smart_processing_call() -> None:
    queue = SmartProcessingQueue(coro_fn, 10)
    big_work = map(queue, map(str, range(100)))
    results = await asyncio.gather(*big_work)
    assert results == list(range(100))
    assert queue.empty()


@asyncio_cooperative
async def test_priority_processing_call() -> None:
    queue = PriorityProcessingQueue(coro_fn, 10)
    big_work = (queue(i, str(i)) for i in range(100))
    results = await asyncio.gather(*big_work)
    assert results == list(range(100))
    assert queue.empty()
