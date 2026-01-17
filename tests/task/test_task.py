import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any, TypeVar, cast

import pytest

from a_sync import TaskMapping, a_sync, create_task
from a_sync.a_sync.base import ASyncGenericBase
from a_sync.a_sync.function import (ASyncFunction,  # type: ignore[attr-defined]
                                    ASyncFunctionAsyncDefault, ASyncFunctionSyncDefault,
                                    _ASyncFunction)
from a_sync.a_sync.method import (ASyncBoundMethod,  # type: ignore[attr-defined]
                                  ASyncBoundMethodAsyncDefault, ASyncBoundMethodSyncDefault,
                                  _ASyncBoundMethod)
from a_sync.task import _EmptySequenceError, _unwrap

_F = TypeVar("_F", bound=Callable[..., Any])
asyncio_cooperative = cast(Callable[[_F], _F], pytest.mark.asyncio_cooperative)
a_sync_typed = cast(Callable[[_F], _F], a_sync)
a_sync_sync = cast(Callable[[_F], _F], a_sync("sync"))
a_sync_async = cast(Callable[[_F], _F], a_sync("async"))


async def _coro_fn(key: int) -> str:
    """Coroutine function for testing.

    Args:
        i: An integer input.

    Returns:
        A string representation of the incremented input.

    See Also:
        - :func:`a_sync.TaskMapping`
    """
    await asyncio.sleep(0.1)
    return str(key + 1) * (key + 1)


@asyncio_cooperative
async def test_create_task() -> None:
    """Test the creation of an asynchronous task.

    Verifies that a task can be created using the `create_task`
    function with a coroutine and a specified name.

    See Also:
        - :func:`a_sync.create_task`
    """
    t = create_task(coro=asyncio.sleep(0), name="test")
    assert t.get_name() == "test", t
    await t


@asyncio_cooperative
async def test_persistent_task() -> None:  # sourcery skip: simplify-boolean-comparison
    """Test the persistence of a task without a local reference.

    Checks if a task created without a local reference
    completes successfully by setting a nonlocal variable.
    The test ensures that the task completes by verifying
    the change in the nonlocal variable.

    See Also:
        - :func:`a_sync.create_task`
    """
    check = False

    async def task() -> None:
        await asyncio.sleep(1)
        nonlocal check
        check = True

    create_task(coro=task(), skip_gc_until_done=True)
    # there is no local reference to the newly created task. does it still complete?
    await asyncio.sleep(2)
    assert check is True


@asyncio_cooperative
async def test_pruning() -> None:
    """Test task creation and handling without errors.

    Ensures that tasks can be created without causing errors.
    This test does not explicitly check for task pruning, despite
    its name, but rather focuses on task creation stability.

    See Also:
        - :func:`a_sync.create_task`
    """

    async def task() -> None:
        return

    create_task(coro=task(), skip_gc_until_done=True)
    await asyncio.sleep(0)
    # previously, it failed here
    create_task(coro=task(), skip_gc_until_done=True)


@asyncio_cooperative
async def test_task_mapping_init() -> None:
    """Test initialization of TaskMapping.

    Verifies that the :class:`TaskMapping` class initializes correctly
    with the provided coroutine function and arguments. Checks
    the handling of function arguments and the task name.

    See Also:
        - :class:`a_sync.TaskMapping`
    """
    tasks = TaskMapping(_coro_fn)
    wrapped_func = cast(Any, tasks._wrapped_func)
    assert wrapped_func is _coro_fn, f"{wrapped_func} , {_coro_fn}, {wrapped_func == _coro_fn}"
    assert tasks._wrapped_func_kwargs == {}
    assert tasks._name is None
    tasks = TaskMapping(_coro_fn, name="test", kwarg0=1, kwarg1=None)
    assert tasks._wrapped_func_kwargs == {"kwarg0": 1, "kwarg1": None}
    assert tasks._name == "test"


@asyncio_cooperative
async def test_task_mapping() -> None:
    """Test the functionality of TaskMapping.

    Checks the behavior of :class:`TaskMapping`, including task
    creation, retrieval, and execution. Verifies the ability
    to await the mapping and checks the return values of tasks.

    See Also:
        - :class:`a_sync.TaskMapping`
    """
    tasks = TaskMapping(_coro_fn)
    # does it return the correct type
    assert isinstance(tasks[0], asyncio.Task)
    # does it correctly return existing values
    assert tasks[1] is tasks[1]
    # does the task return the correct value
    assert await tasks[0] == "1"
    # can it do it again
    assert await tasks[0] == "1"
    # can we await the mapping?
    assert await tasks == {0: "1", 1: "22"}
    # can we await one from scratch?
    assert await TaskMapping(_coro_fn, range(5)) == {
        0: "1",
        1: "22",
        2: "333",
        3: "4444",
        4: "55555",
    }
    assert len(tasks) == 2


@asyncio_cooperative
async def test_task_mapping_map_with_sync_iter() -> None:
    """Test TaskMapping with a synchronous iterator.

    Verifies that :class:`TaskMapping` can map over a synchronous
    iterator and correctly handle keys, values, and items.
    Ensures that mapping in progress raises a :class:`RuntimeError`
    when attempted concurrently.

    See Also:
        - :class:`a_sync.TaskMapping`
    """
    tasks = TaskMapping(_coro_fn)
    i = 0
    async for k, v in cast(Any, tasks).map(range(5)):
        assert isinstance(k, int)
        assert isinstance(v, str)
        if i < 4:
            # this shouldn't work since there is a mapping in progress
            with pytest.raises(RuntimeError):
                async for k in cast(Any, tasks).map(range(5)):
                    ...
        i += 1
    tasks = TaskMapping(_coro_fn)
    async for k in cast(Any, tasks).map(range(5), pop=False, yields="keys"):
        assert isinstance(k, int)

    # test keys
    for k in tasks.keys():
        assert isinstance(k, int)
    awaited_keys = await tasks.keys()
    assert isinstance(awaited_keys, list)
    for k in awaited_keys:
        assert isinstance(k, int)
    async for k in tasks.keys():
        assert isinstance(k, int)

    # test values
    for v in cast(Any, tasks.values()):
        assert isinstance(v, asyncio.Future)
        assert isinstance(await v, str)
    awaited_values = await tasks.values()
    assert isinstance(awaited_values, list)
    for v in awaited_values:
        assert isinstance(v, str)
    async for v in tasks.values():
        assert isinstance(v, str)

    # test items
    for k, v in cast(Any, tasks.items()):
        assert isinstance(k, int)
        assert isinstance(v, asyncio.Future)
        assert isinstance(await v, str)
    awaited_items = cast(list[tuple[int, str]], await cast(Any, tasks.items()))
    assert isinstance(awaited_items, list)
    for k, v in awaited_items:
        assert isinstance(k, int)
        assert isinstance(v, str)
    async for k, v in cast(Any, tasks.items()):
        assert isinstance(k, int)
        assert isinstance(v, str)


@asyncio_cooperative
async def test_task_mapping_map_with_async_iter() -> None:
    """Test TaskMapping with an asynchronous iterator.

    Verifies that :class:`TaskMapping` can map over an asynchronous
    iterator and correctly handle keys, values, and items.
    Ensures that mapping in progress raises a :class:`RuntimeError`
    when attempted concurrently.

    See Also:
        - :class:`a_sync.TaskMapping`
    """

    async def async_iter() -> AsyncIterator[int]:
        for i in range(5):
            yield i

    tasks = TaskMapping(_coro_fn)
    i = 0
    async for k, v in cast(Any, tasks).map(async_iter()):
        assert isinstance(k, int)
        assert isinstance(v, str)
        if i < 4:
            # this shouldn't work since there is a mapping in progress
            with pytest.raises(RuntimeError):
                async for k in cast(Any, tasks).map(async_iter()):
                    ...
        i += 1
    tasks = TaskMapping(_coro_fn)
    async for k in cast(Any, tasks).map(async_iter(), pop=False, yields="keys"):
        assert isinstance(k, int)

    # test keys
    for k in tasks.keys():
        assert isinstance(k, int)
    awaited_keys = await tasks.keys()
    assert isinstance(awaited_keys, list)
    for k in awaited_keys:
        assert isinstance(k, int)
    async for k in tasks.keys():
        assert isinstance(k, int)
    assert await tasks.keys().aiterbykeys() == list(range(5))
    assert await tasks.keys().aiterbyvalues() == list(range(5))
    assert await tasks.keys().aiterbykeys(reverse=True) == sorted(range(5), reverse=True)
    assert await tasks.keys().aiterbyvalues(reverse=True) == sorted(range(5), reverse=True)

    # test values
    for v in cast(Any, tasks.values()):
        assert isinstance(v, asyncio.Future)
        assert isinstance(await v, str)
    awaited_values = await tasks.values()
    assert isinstance(awaited_values, list)
    for v in awaited_values:
        assert isinstance(v, str)
    async for v in tasks.values():
        assert isinstance(v, str)
    assert await tasks.values().aiterbykeys() == [str(i) * i for i in range(1, 6)]
    assert await tasks.values().aiterbyvalues() == [str(i) * i for i in range(1, 6)]
    assert await tasks.values().aiterbykeys(reverse=True) == [
        str(i) * i for i in sorted(range(1, 6), reverse=True)
    ]
    assert await tasks.values().aiterbyvalues(reverse=True) == [
        str(i) * i for i in sorted(range(1, 6), reverse=True)
    ]

    # test items
    for k, v in cast(Any, tasks.items()):
        assert isinstance(k, int)
        assert isinstance(v, asyncio.Future)
        assert isinstance(await v, str)
    awaited_items = cast(list[tuple[int, str]], await cast(Any, tasks.items()))
    assert isinstance(awaited_items, list)
    for k, v in awaited_items:
        assert isinstance(k, int)
        assert isinstance(v, str)
    async for k, v in cast(Any, tasks.items()):
        assert isinstance(k, int)
        assert isinstance(v, str)
    items_view = cast(Any, tasks.items())
    assert await items_view.aiterbykeys() == [(i, str(i + 1) * (i + 1)) for i in range(5)]
    assert await items_view.aiterbyvalues() == [(i, str(i + 1) * (i + 1)) for i in range(5)]
    assert await items_view.aiterbykeys(reverse=True) == [
        (i, str(i + 1) * (i + 1)) for i in sorted(range(5), reverse=True)
    ]
    assert await cast(Any, tasks.items(pop=True)).aiterbyvalues(reverse=True) == [
        (i, str(i + 1) * (i + 1)) for i in sorted(range(5), reverse=True)
    ]
    assert not tasks  # did pop work?


def test_taskmapping_views_sync() -> None:
    """Test synchronous views of TaskMapping.

    Checks the synchronous access to keys, values, and items
    in :class:`TaskMapping`. Verifies the state of these views before
    and after gathering tasks.

    See Also:
        - :class:`a_sync.TaskMapping`
    """
    tasks = TaskMapping(_coro_fn, range(5))

    # keys are currently empty until the loop has a chance to run
    _assert_len_dictviews(tasks, 0)
    cast(Any, tasks).gather()

    _assert_len_dictviews(tasks, 5)
    for k in tasks.keys():
        assert isinstance(k, int)

    # test values
    for v in tasks.values():
        assert isinstance(v, asyncio.Future)

    # test items
    for k, v in tasks.items():
        assert isinstance(k, int)
        assert isinstance(v, asyncio.Future)

    assert len(tasks.keys()) == 5
    for k in tasks.keys():
        assert isinstance(k, int)


@asyncio_cooperative
async def test_task_mapping_empty_iterable() -> None:
    """Test TaskMapping with an empty iterable."""
    tasks = TaskMapping(_coro_fn, [])
    assert len(tasks) == 0
    with pytest.raises(_EmptySequenceError, match=r"\[\]"):
        await tasks


@asyncio_cooperative
async def test_task_mapping_single_item() -> None:
    """Test TaskMapping with a single-item iterable."""
    tasks = TaskMapping(_coro_fn, [0])
    await asyncio.sleep(0.01)
    assert len(tasks) == 1
    assert await tasks == {0: "1"}


@asyncio_cooperative
async def test_task_mapping_error_handling() -> None:
    """Test TaskMapping with a function that raises an exception."""

    async def error_fn(key: int) -> str:
        raise ValueError("Intentional error")

    tasks = TaskMapping(error_fn, [0])
    with pytest.raises(ValueError):
        await tasks


@asyncio_cooperative
async def test_task_mapping_concurrency() -> None:
    """Test TaskMapping with a concurrency limit."""
    tasks = TaskMapping(_coro_fn, range(10), concurrency=3)
    running_tasks = [task for task in cast(Any, tasks.values()) if not task.done()]
    assert len(running_tasks) <= 3


def _assert_len_dictviews(tasks: TaskMapping[int, str], expected: int) -> None:
    assert len(tasks.keys()) == expected
    assert len(tasks.values()) == expected
    assert len(tasks.items()) == expected


# TODO: add unwrap tests for bound method and property classes
def test_unwrap_basic() -> None:
    async def test_fn() -> None: ...

    unwrapped: Any = _unwrap(cast(Any, test_fn))
    assert unwrapped is test_fn


def test_unwrap_a_sync_function_sync_def() -> None:
    @a_sync_typed
    def test_fn() -> None: ...

    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, ASyncFunction)
    test_fn_any = cast(Any, test_fn)
    unwrapped: Any = _unwrap(test_fn_any)
    assert unwrapped is not test_fn
    assert unwrapped is not test_fn_any.__wrapped__
    assert unwrapped is test_fn_any._asyncified
    assert not isinstance(unwrapped, _ASyncFunction)
    assert not isinstance(unwrapped, ASyncFunction)


def test_unwrap_a_sync_function_async_def() -> None:
    @a_sync_typed
    async def test_fn() -> None: ...

    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, ASyncFunction)
    test_fn_any = cast(Any, test_fn)
    unwrapped: Any = _unwrap(test_fn_any)
    assert unwrapped is not test_fn
    assert unwrapped is test_fn_any.__wrapped__
    assert unwrapped is test_fn_any._modified_fn
    assert not isinstance(unwrapped, _ASyncFunction)
    assert not isinstance(unwrapped, ASyncFunction)


def test_unwrap_a_sync_function_sync_def_sync_default() -> None:
    @a_sync_sync
    def test_fn() -> None: ...

    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, ASyncFunctionSyncDefault)
    test_fn_any = cast(Any, test_fn)
    unwrapped: Any = _unwrap(test_fn_any)
    assert unwrapped is not test_fn
    assert unwrapped is not test_fn_any.__wrapped__
    assert unwrapped is test_fn_any._asyncified
    assert not isinstance(unwrapped, _ASyncFunction)
    assert not isinstance(unwrapped, ASyncFunction)


def test_unwrap_a_sync_function_async_def_sync_default() -> None:
    @a_sync_sync
    async def test_fn() -> None: ...

    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, ASyncFunctionSyncDefault)
    test_fn_any = cast(Any, test_fn)
    unwrapped: Any = _unwrap(test_fn_any)
    assert unwrapped is not test_fn
    assert unwrapped is test_fn_any.__wrapped__
    assert unwrapped is test_fn_any._modified_fn
    assert not isinstance(unwrapped, _ASyncFunction)
    assert not isinstance(unwrapped, ASyncFunction)


def test_unwrap_a_sync_function_sync_def_async_default() -> None:
    @a_sync_async
    def test_fn() -> None: ...

    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, ASyncFunctionAsyncDefault)
    test_fn_any = cast(Any, test_fn)
    unwrapped: Any = _unwrap(test_fn_any)
    assert unwrapped is not test_fn
    assert unwrapped is not test_fn_any.__wrapped__
    assert unwrapped is test_fn_any._asyncified
    assert not isinstance(unwrapped, _ASyncFunction)
    assert not isinstance(unwrapped, ASyncFunction)


def test_unwrap_a_sync_function_async_def_async_default() -> None:
    @a_sync_async
    async def test_fn() -> None: ...

    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, ASyncFunctionAsyncDefault)
    test_fn_any = cast(Any, test_fn)
    unwrapped: Any = _unwrap(test_fn_any)
    assert unwrapped is not test_fn
    assert unwrapped is test_fn_any.__wrapped__
    assert unwrapped is test_fn_any._modified_fn
    assert not isinstance(unwrapped, _ASyncFunction)
    assert not isinstance(unwrapped, ASyncFunction)


def test_unwrap_a_sync_method_sync_def() -> None:
    class MyClass(ASyncGenericBase):
        def __init__(self, sync: bool) -> None:
            self.sync = sync
            super().__init__()

        def test_fn(self) -> None: ...

    test_fn = MyClass(sync=True).test_fn
    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, _ASyncBoundMethod)
    assert isinstance(test_fn, ASyncBoundMethod)
    unwrapped: Any = _unwrap(cast(Any, test_fn))
    assert unwrapped is test_fn


def test_unwrap_a_sync_method_async_def() -> None:
    class MyClass(ASyncGenericBase):
        def __init__(self, sync: bool) -> None:
            self.sync = sync
            super().__init__()

        async def test_fn(self) -> None: ...

    test_fn = MyClass(sync=True).test_fn
    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, _ASyncBoundMethod)
    assert isinstance(test_fn, ASyncBoundMethod)
    unwrapped: Any = _unwrap(cast(Any, test_fn))
    assert unwrapped is test_fn


def test_unwrap_a_sync_method_sync_def_sync_defult() -> None:
    class MyClass(ASyncGenericBase):
        def __init__(self, sync: bool) -> None:
            self.sync = sync
            super().__init__()

        @a_sync_sync
        def test_fn(self) -> None: ...

    test_fn = MyClass(sync=True).test_fn
    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, _ASyncBoundMethod)
    assert isinstance(test_fn, ASyncBoundMethodSyncDefault)
    unwrapped: Any = _unwrap(cast(Any, test_fn))
    assert unwrapped is test_fn


def test_unwrap_a_sync_method_async_def_sync_defult() -> None:
    class MyClass(ASyncGenericBase):
        def __init__(self, sync: bool) -> None:
            self.sync = sync
            super().__init__()

        @a_sync_sync
        async def test_fn(self) -> None: ...

    test_fn = MyClass(sync=True).test_fn
    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, _ASyncBoundMethod)
    assert isinstance(test_fn, ASyncBoundMethodSyncDefault)
    unwrapped: Any = _unwrap(cast(Any, test_fn))
    assert unwrapped is test_fn


def test_unwrap_a_sync_method_sync_def_async_default() -> None:
    class MyClass(ASyncGenericBase):
        def __init__(self, sync: bool) -> None:
            self.sync = sync
            super().__init__()

        @a_sync_async
        def test_fn(self) -> None: ...

    test_fn = MyClass(sync=True).test_fn
    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, _ASyncBoundMethod)
    assert isinstance(test_fn, ASyncBoundMethodAsyncDefault)
    unwrapped: Any = _unwrap(cast(Any, test_fn))
    assert unwrapped is test_fn


def test_unwrap_a_sync_method_async_def_async_default() -> None:
    class MyClass(ASyncGenericBase):
        def __init__(self, sync: bool) -> None:
            self.sync = sync
            super().__init__()

        @a_sync_async
        async def test_fn(self) -> None: ...

    test_fn = MyClass(sync=True).test_fn
    assert isinstance(test_fn, _ASyncFunction)
    assert isinstance(test_fn, _ASyncBoundMethod)
    assert isinstance(test_fn, ASyncBoundMethodAsyncDefault)
    unwrapped: Any = _unwrap(cast(Any, test_fn))
    assert unwrapped is test_fn
