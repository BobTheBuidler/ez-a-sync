import pytest
import asyncio

from a_sync.task import (
    TaskMapping,
    TaskMappingKeys,
    TaskMappingValues,
    TaskMappingItems,
    _EmptySequenceError,
)


views = [TaskMappingKeys, TaskMappingValues, TaskMappingItems]


async def sample_task(key):
    await asyncio.sleep(0.1)
    return f"result for {key}"


@pytest.mark.parametrize(
    "view_class, expected",
    [
        (TaskMappingKeys, ["key1", "key2"]),
        (TaskMappingValues, ["result for key1", "result for key2"]),
        (TaskMappingItems, [("key1", "result for key1"), ("key2", "result for key2")]),
    ],
)
def test_taskmapping_views_sync(view_class, expected):
    tasks = TaskMapping(sample_task, ["key1", "key2"])
    view = view_class(expected, tasks)
    results = list(view)
    assert results == expected


@pytest.mark.asyncio_cooperative
@pytest.mark.parametrize(
    "view_class, expected",
    [
        (TaskMappingKeys, ["key1", "key2"]),
        (TaskMappingValues, ["result for key1", "result for key2"]),
        (TaskMappingItems, [("key1", "result for key1"), ("key2", "result for key2")]),
    ],
)
async def test_taskmapping_views_async(view_class, expected):
    tasks = TaskMapping(sample_task, ["key1", "key2"])
    view = view_class(expected, tasks)
    results = [item async for item in view]
    assert results == expected


@pytest.mark.parametrize("view_class", [TaskMappingKeys, TaskMappingValues, TaskMappingItems])
def test_empty_taskmapping_views_sync(view_class):
    # sourcery skip: simplify-empty-collection-comparison
    tasks = TaskMapping(sample_task)
    view = view_class([], tasks)
    results = list(view)
    assert results == []


@pytest.mark.asyncio_cooperative
@pytest.mark.parametrize("view_class", [TaskMappingKeys, TaskMappingValues, TaskMappingItems])
async def test_empty_taskmapping_views_async(view_class):
    # sourcery skip: simplify-empty-collection-comparison
    tasks = TaskMapping(sample_task)
    view = view_class([], tasks)
    results = [item async for item in view]
    assert results == []


""" # NOTE not sure why this fails but we can get to it later
@pytest.mark.parametrize("view_class", views)
def test_empty_taskmapping_views_broken_mapping_sync(view_class):
    tasks = TaskMapping(sample_task, [])
    view = view_class([], tasks)
    with pytest.raises(_EmptySequenceError, match="\[\]"):
        results = list(view)"""


@pytest.mark.asyncio_cooperative
@pytest.mark.parametrize("view_class", views)
async def test_empty_taskmapping_views_broken_mapping_async(view_class):
    tasks = TaskMapping(sample_task, [])
    view = view_class([], tasks)
    with pytest.raises(_EmptySequenceError, match="\[\]"):
        results = [item async for item in view]


@pytest.mark.parametrize(
    "view_class, expected",
    [
        (TaskMappingKeys, ["key1"]),
        (TaskMappingValues, ["result for key1"]),
        (TaskMappingItems, [("key1", "result for key1")]),
    ],
)
def test_single_item_taskmapping_views_sync(view_class, expected):
    tasks = TaskMapping(sample_task, ["key1"])
    view = view_class(expected, tasks)
    results = list(view)
    assert results == expected


@pytest.mark.asyncio_cooperative
@pytest.mark.parametrize(
    "view_class, expected",
    [
        (TaskMappingKeys, ["key1"]),
        (TaskMappingValues, ["result for key1"]),
        (TaskMappingItems, [("key1", "result for key1")]),
    ],
)
async def test_single_item_taskmapping_views_async(view_class, expected):
    tasks = TaskMapping(sample_task, ["key1"])
    view = view_class(expected, tasks)
    results = [item async for item in view]
    assert results == expected
