import asyncio
import pytest

from a_sync.utils.iterators import as_yielded


# Helpers
class AsyncGen:
    def __init__(self, values, delay=0):
        self.values = list(values)
        self.delay = delay

    def __aiter__(self):
        self._idx = 0
        return self

    async def __anext__(self):
        if self._idx >= len(self.values):
            raise StopAsyncIteration
        val = self.values[self._idx]
        self._idx += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return val


class ErrorGen:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise Exception("Iterator Error!")


@pytest.mark.asyncio_cooperative
async def test_simple_merge():
    gen1 = AsyncGen([1, 2, 3])
    gen2 = AsyncGen([10, 20])
    results = set()
    async for item in as_yielded(gen1, gen2):
        results.add(item)
    assert results == {1, 2, 3, 10, 20}


@pytest.mark.asyncio_cooperative
async def test_merge_with_empty():
    gen_empty = AsyncGen([])
    gen_full = AsyncGen([5])
    results = []
    async for item in as_yielded(gen_empty, gen_full):
        results.append(item)
    assert results == [5]


@pytest.mark.asyncio_cooperative
async def test_merge_slow_fast():
    fast = AsyncGen([1, 2, 3], delay=0.01)
    slow = AsyncGen(["a", "b"], delay=0.05)
    got = []
    async for item in as_yielded(fast, slow):
        got.append(item)
    # All should appear, timing for order is implementation dependent.
    assert set(got) == {1, 2, 3, "a", "b"}


@pytest.mark.asyncio_cooperative
async def test_error_in_iterator():
    error_gen = ErrorGen()
    ok_gen = AsyncGen([4, 5])
    got = []
    with pytest.raises(Exception, match="Iterator Error!"):
        async for item in as_yielded(error_gen, ok_gen):
            got.append(item)


@pytest.mark.asyncio_cooperative
async def test_single_iterator():
    gen = AsyncGen(range(5))
    results = []
    async for item in as_yielded(gen):
        results.append(item)
    assert results == [0, 1, 2, 3, 4]


@pytest.mark.asyncio_cooperative
async def test_all_empty_iterators():
    gens = [AsyncGen([]) for _ in range(3)]
    results = []
    async for item in as_yielded(*gens):
        results.append(item)
    assert results == []


@pytest.mark.asyncio_cooperative
async def test_consumer_cancels_early():
    # If the consumer stops early, as_yielded should not misbehave or deadlock.
    gen = AsyncGen(range(100))
    count = 0
    async for item in as_yielded(gen):
        count += 1
        if count >= 5:
            break
    assert count == 5
