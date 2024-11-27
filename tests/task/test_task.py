import asyncio
import pytest

from a_sync import TaskMapping, create_task
from a_sync.task import _EmptySequenceError


async def _coro_fn(key):
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


@pytest.mark.asyncio_cooperative
async def test_create_task():
    """Test the creation of an asynchronous task.

    Verifies that a task can be created using the `create_task`
    function with a coroutine and a specified name.

    See Also:
        - :func:`a_sync.create_task`
    """
    t = create_task(coro=asyncio.sleep(0), name="test")
    assert t.get_name() == "test", t
    await t


@pytest.mark.asyncio_cooperative
async def test_persistent_task():  # sourcery skip: simplify-boolean-comparison
    """Test the persistence of a task without a local reference.

    Checks if a task created without a local reference
    completes successfully by setting a nonlocal variable.
    The test ensures that the task completes by verifying
    the change in the nonlocal variable.

    See Also:
        - :func:`a_sync.create_task`
    """
    check = False

    async def task():
        await asyncio.sleep(1)
        nonlocal check
        check = True

    create_task(coro=task(), skip_gc_until_done=True)
    # there is no local reference to the newly created task. does it still complete?
    await asyncio.sleep(2)
    assert check is True


@pytest.mark.asyncio_cooperative
async def test_pruning():
    """Test task creation and handling without errors.

    Ensures that tasks can be created without causing errors.
    This test does not explicitly check for task pruning, despite
    its name, but rather focuses on task creation stability.

    See Also:
        - :func:`a_sync.create_task`
    """

    async def task():
        return

    create_task(coro=task(), skip_gc_until_done=True)
    await asyncio.sleep(0)
    # previously, it failed here
    create_task(coro=task(), skip_gc_until_done=True)


@pytest.mark.asyncio_cooperative
async def test_task_mapping_init():
    """Test initialization of TaskMapping.

    Verifies that the :class:`TaskMapping` class initializes correctly
    with the provided coroutine function and arguments. Checks
    the handling of function arguments and the task name.

    See Also:
        - :class:`a_sync.TaskMapping`
    """
    tasks = TaskMapping(_coro_fn)
    assert (
        tasks._wrapped_func is _coro_fn
    ), f"{tasks._wrapped_func} , {_coro_fn}, {tasks._wrapped_func == _coro_fn}"
    assert tasks._wrapped_func_kwargs == {}
    assert tasks._name is None
    tasks = TaskMapping(_coro_fn, name="test", kwarg0=1, kwarg1=None)
    assert tasks._wrapped_func_kwargs == {"kwarg0": 1, "kwarg1": None}
    assert tasks._name == "test"


@pytest.mark.asyncio_cooperative
async def test_task_mapping():
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


@pytest.mark.asyncio_cooperative
async def test_task_mapping_map_with_sync_iter():
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
    async for k, v in tasks.map(range(5)):
        assert isinstance(k, int)
        assert isinstance(v, str)
        if i < 4:
            # this shouldn't work since there is a mapping in progress
            with pytest.raises(RuntimeError):
                async for k in tasks.map(range(5)):
                    ...
        i += 1
    tasks = TaskMapping(_coro_fn)
    async for k in tasks.map(range(5), pop=False, yields="keys"):
        assert isinstance(k, int)

    # test keys
    for k in tasks.keys():
        assert isinstance(k, int)
    awaited = await tasks.keys()
    assert isinstance(awaited, list)
    for k in awaited:
        assert isinstance(k, int)
    async for k in tasks.keys():
        assert isinstance(k, int)

    # test values
    for v in tasks.values():
        assert isinstance(v, asyncio.Future)
        assert isinstance(await v, str)
    awaited = await tasks.values()
    assert isinstance(awaited, list)
    for v in awaited:
        assert isinstance(v, str)
    async for v in tasks.values():
        assert isinstance(v, str)

    # test items
    for k, v in tasks.items():
        assert isinstance(k, int)
        assert isinstance(v, asyncio.Future)
        assert isinstance(await v, str)
    awaited = await tasks.items()
    assert isinstance(awaited, list)
    for k, v in awaited:
        assert isinstance(k, int)
        assert isinstance(v, str)
    async for k, v in tasks.items():
        assert isinstance(k, int)
        assert isinstance(v, str)


@pytest.mark.asyncio_cooperative
async def test_task_mapping_map_with_async_iter():
    """Test TaskMapping with an asynchronous iterator.

    Verifies that :class:`TaskMapping` can map over an asynchronous
    iterator and correctly handle keys, values, and items.
    Ensures that mapping in progress raises a :class:`RuntimeError`
    when attempted concurrently.

    See Also:
        - :class:`a_sync.TaskMapping`
    """

    async def async_iter():
        for i in range(5):
            yield i

    tasks = TaskMapping(_coro_fn)
    i = 0
    async for k, v in tasks.map(async_iter()):
        assert isinstance(k, int)
        assert isinstance(v, str)
        if i < 4:
            # this shouldn't work since there is a mapping in progress
            with pytest.raises(RuntimeError):
                async for k in tasks.map(async_iter()):
                    ...
        i += 1
    tasks = TaskMapping(_coro_fn)
    async for k in tasks.map(async_iter(), pop=False, yields="keys"):
        assert isinstance(k, int)

    # test keys
    for k in tasks.keys():
        assert isinstance(k, int)
    awaited = await tasks.keys()
    assert isinstance(awaited, list)
    for k in awaited:
        assert isinstance(k, int)
    async for k in tasks.keys():
        assert isinstance(k, int)
    assert await tasks.keys().aiterbykeys() == list(range(5))
    assert await tasks.keys().aiterbyvalues() == list(range(5))
    assert await tasks.keys().aiterbykeys(reverse=True) == sorted(range(5), reverse=True)
    assert await tasks.keys().aiterbyvalues(reverse=True) == sorted(range(5), reverse=True)

    # test values
    for v in tasks.values():
        assert isinstance(v, asyncio.Future)
        assert isinstance(await v, str)
    awaited = await tasks.values()
    assert isinstance(awaited, list)
    for v in awaited:
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
    for k, v in tasks.items():
        assert isinstance(k, int)
        assert isinstance(v, asyncio.Future)
        assert isinstance(await v, str)
    awaited = await tasks.items()
    assert isinstance(awaited, list)
    for k, v in awaited:
        assert isinstance(k, int)
        assert isinstance(v, str)
    async for k, v in tasks.items():
        assert isinstance(k, int)
        assert isinstance(v, str)
    assert await tasks.items().aiterbykeys() == [(i, str(i + 1) * (i + 1)) for i in range(5)]
    assert await tasks.items().aiterbyvalues() == [(i, str(i + 1) * (i + 1)) for i in range(5)]
    assert await tasks.items().aiterbykeys(reverse=True) == [
        (i, str(i + 1) * (i + 1)) for i in sorted(range(5), reverse=True)
    ]
    assert await tasks.items(pop=True).aiterbyvalues(reverse=True) == [
        (i, str(i + 1) * (i + 1)) for i in sorted(range(5), reverse=True)
    ]
    assert not tasks  # did pop work?


def test_taskmapping_views_sync():
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
    tasks.gather()

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


@pytest.mark.asyncio_cooperative
async def test_task_mapping_empty_iterable():
    """Test TaskMapping with an empty iterable."""
    tasks = TaskMapping(_coro_fn, [])
    assert len(tasks) == 0
    with pytest.raises(_EmptySequenceError, match="\[\]"):
        await tasks


@pytest.mark.asyncio_cooperative
async def test_task_mapping_single_item():
    """Test TaskMapping with a single-item iterable."""
    tasks = TaskMapping(_coro_fn, [0])
    await asyncio.sleep(0.01)
    assert len(tasks) == 1
    assert await tasks == {0: "1"}


@pytest.mark.asyncio_cooperative
async def test_task_mapping_error_handling():
    """Test TaskMapping with a function that raises an exception."""

    async def error_fn(key):
        raise ValueError("Intentional error")

    tasks = TaskMapping(error_fn, [0])
    with pytest.raises(ValueError):
        await tasks


@pytest.mark.asyncio_cooperative
async def test_task_mapping_concurrency():
    """Test TaskMapping with a concurrency limit."""
    tasks = TaskMapping(_coro_fn, range(10), concurrency=3)
    running_tasks = [task for task in tasks.values() if not task.done()]
    assert len(running_tasks) <= 3


def _assert_len_dictviews(tasks, i):
    assert len(tasks.keys()) == i
    assert len(tasks.values()) == i
    assert len(tasks.items()) == i
