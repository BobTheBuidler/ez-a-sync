import asyncio
import time
from threading import current_thread, main_thread
from typing import Literal

import pytest

import a_sync
from a_sync import ASyncBase
from a_sync.a_sync._meta import ASyncMeta, ASyncSingletonMeta
from a_sync.a_sync.singleton import ASyncGenericSingleton

increment = pytest.mark.parametrize("i", range(10))


class WrongThreadError(Exception): ...


class TestClass(ASyncBase):
    def __init__(self, v: int, sync: bool = False):
        self.v = v
        self.sync = sync
        super().__init__()

    async def test_fn(self) -> int:
        if self.sync == False and main_thread() != current_thread():
            raise WrongThreadError("This should be running on an event loop in the main thread.")
        elif self.sync == True and main_thread() != current_thread():
            raise WrongThreadError("This should be awaited in the main thread")
        assert (
            TestClass.test_fn.__is_async_def__ is True
        ), f"{TestClass.test_fn.__is_async_def__} is not True"
        return self.v

    @a_sync.aka.property
    async def test_property(self) -> int:
        if self.sync == False and main_thread() != current_thread():
            raise WrongThreadError("This should be running on an event loop in the main thread.")
        elif self.sync == True and main_thread() != current_thread():
            raise WrongThreadError("This should be awaited in the main thread")
        return self.v * 2

    @a_sync.alias.cached_property
    async def test_cached_property(self) -> int:
        if self.sync == False and main_thread() != current_thread():
            raise WrongThreadError("This should be running on an event loop in the main thread.")
        elif self.sync == True and main_thread() != current_thread():
            raise WrongThreadError("This should be awaited in the main thread")
        await asyncio.sleep(2)
        return self.v * 3


class TestSync(ASyncBase):
    main = main_thread()

    def __init__(self, v: int, sync: bool):
        self.v = v
        self.sync = sync
        super().__init__()

    def test_fn(self) -> int:
        # Sync bound methods are actually async functions that are run in an executor and awaited
        if self.sync == False and main_thread() == current_thread():
            raise WrongThreadError("This should be running in an executor, not the main thread.")
        elif self.sync == True and main_thread() != current_thread():
            raise WrongThreadError("This should be running synchronously in the main thread")
        assert (
            TestSync.test_fn.__is_async_def__ is False
        ), f"{TestSync.test_fn.__is_async_def__} is not False"
        return self.v

    @a_sync.aka.property
    def test_property(self) -> int:
        if self.sync == False and main_thread() == current_thread():
            raise WrongThreadError("This should be running in an executor, not the main thread.")
        if self.sync == True and main_thread() == current_thread():
            # Sync properties are actually async functions that are run in an executor and awaited
            raise WrongThreadError("This should be running in an executor, not the main thread.")
        return self.v * 2

    @a_sync.alias.cached_property
    def test_cached_property(self) -> int:
        if self.sync == False and main_thread() == current_thread():
            raise WrongThreadError("This should be running in an executor, not the main thread.")
        if self.sync == True and main_thread() == current_thread():
            # Sync properties are actually async functions that are run in an executor and awaited
            raise WrongThreadError("This should be running in an executor, not the main thread.")
        time.sleep(2)
        return self.v * 3


class TestLimiter(TestClass):
    limiter = 1


class TestInheritor(TestClass):
    pass


class TestMeta(TestClass, metaclass=ASyncMeta):
    pass


class TestSingleton(ASyncGenericSingleton, TestClass):
    runs_per_minute = 100
    pass


class TestSingletonMeta(TestClass, metaclass=ASyncSingletonMeta):
    semaphore = 1
    pass


class TestSemaphore(ASyncBase):
    # semaphore=1  # NOTE: this is detected propely by undecorated test_fn but not the properties

    def __init__(self, v: int, sync: bool):
        self.v = v
        self.sync = sync
        super().__init__()

    # spec on class and function both working
    @a_sync.a_sync(semaphore=1)
    async def test_fn(self) -> int:
        await asyncio.sleep(1)
        return self.v

    # spec on class, function, property all working
    @a_sync.aka.property("async", semaphore=1)
    async def test_property(self) -> int:
        await asyncio.sleep(1)
        return self.v * 2

    # spec on class, function, property all working
    @a_sync.alias.cached_property(semaphore=50)
    async def test_cached_property(self) -> int:
        await asyncio.sleep(1)
        return self.v * 3


def _test_kwargs(fn, default: Literal["sync", "async", None]):
    # force async
    assert asyncio.get_event_loop().run_until_complete(fn(sync=False)) == 2
    assert asyncio.get_event_loop().run_until_complete(fn(asynchronous=True)) == 2
    # force sync
    with pytest.raises(TypeError):
        assert asyncio.get_event_loop().run_until_complete(fn(sync=True)) == 2
    with pytest.raises(TypeError):
        assert asyncio.get_event_loop().run_until_complete(fn(asynchronous=False)) == 2
    assert fn(sync=True) == 2
    assert fn(asynchronous=False) == 2
    if default == "sync":
        assert fn() == 2
    elif default == "async":
        assert asyncio.get_event_loop().run_until_complete(fn()) == 2


async def sample_task(n):
    await asyncio.sleep(0.01)
    return n


async def timeout_task(n):
    await asyncio.sleep(0.1)
    return n


async def sample_exc(n):
    raise ValueError("Sample error")
