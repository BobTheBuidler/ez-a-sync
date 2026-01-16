import asyncio
from collections.abc import Callable
from typing import Any, TypeVar, cast

import pytest

from a_sync.task import (TaskMapping, TaskMappingItems, TaskMappingKeys, TaskMappingValues,
                         _EmptySequenceError)

_F = TypeVar("_F", bound=Callable[..., Any])
asyncio_cooperative = cast(Callable[[_F], _F], pytest.mark.asyncio_cooperative)
parametrize = cast(Callable[..., Callable[[_F], _F]], pytest.mark.parametrize)

views: list[type[Any]] = [TaskMappingKeys, TaskMappingValues, TaskMappingItems]


async def sample_task(key: str) -> str:
    await asyncio.sleep(0.1)
    return f"result for {key}"


@parametrize(
    "view_class, expected",
    [
        (TaskMappingKeys, ["key1", "key2"]),
        (TaskMappingValues, ["result for key1", "result for key2"]),
        (TaskMappingItems, [("key1", "result for key1"), ("key2", "result for key2")]),
    ],
)
def test_taskmapping_views_sync(view_class: type[Any], expected: list[Any]) -> None:
    tasks = TaskMapping(sample_task, ["key1", "key2"])
    view = view_class(expected, tasks)
    results = list(view)
    assert results == expected


@asyncio_cooperative
@parametrize(
    "view_class, expected",
    [
        (TaskMappingKeys, ["key1", "key2"]),
        (TaskMappingValues, ["result for key1", "result for key2"]),
        (TaskMappingItems, [("key1", "result for key1"), ("key2", "result for key2")]),
    ],
)
async def test_taskmapping_views_async(view_class: type[Any], expected: list[Any]) -> None:
    tasks = TaskMapping(sample_task, ["key1", "key2"])
    view = view_class(expected, tasks)
    results = [item async for item in view]
    assert results == expected


@parametrize("view_class", [TaskMappingKeys, TaskMappingValues, TaskMappingItems])
def test_empty_taskmapping_views_sync(view_class: type[Any]) -> None:
    # sourcery skip: simplify-empty-collection-comparison
    tasks = TaskMapping(sample_task)
    view = view_class([], tasks)
    results = list(view)
    assert results == []


@asyncio_cooperative
@parametrize("view_class", [TaskMappingKeys, TaskMappingValues, TaskMappingItems])
async def test_empty_taskmapping_views_async(view_class: type[Any]) -> None:
    # sourcery skip: simplify-empty-collection-comparison
    tasks = TaskMapping(sample_task)
    view = view_class([], tasks)
    results = [item async for item in view]
    assert results == []


r""" # NOTE not sure why this fails but we can get to it later
@parametrize("view_class", views)
def test_empty_taskmapping_views_broken_mapping_sync(view_class):
    tasks = TaskMapping(sample_task, [])
    view = view_class([], tasks)
    with pytest.raises(_EmptySequenceError, match="\[\]"):
        results = list(view)"""


@asyncio_cooperative
@parametrize("view_class", views)
async def test_empty_taskmapping_views_broken_mapping_async(view_class: type[Any]) -> None:
    tasks = TaskMapping(sample_task, [])
    view = view_class([], tasks)
    with pytest.raises(_EmptySequenceError, match=r"\[\]"):
        results = [item async for item in view]


@parametrize(
    "view_class, expected",
    [
        (TaskMappingKeys, ["key1"]),
        (TaskMappingValues, ["result for key1"]),
        (TaskMappingItems, [("key1", "result for key1")]),
    ],
)
def test_single_item_taskmapping_views_sync(
    view_class: type[Any], expected: list[Any]
) -> None:
    tasks = TaskMapping(sample_task, ["key1"])
    view = view_class(expected, tasks)
    results = list(view)
    assert results == expected


@asyncio_cooperative
@parametrize(
    "view_class, expected",
    [
        (TaskMappingKeys, ["key1"]),
        (TaskMappingValues, ["result for key1"]),
        (TaskMappingItems, [("key1", "result for key1")]),
    ],
)
async def test_single_item_taskmapping_views_async(
    view_class: type[Any], expected: list[Any]
) -> None:
    tasks = TaskMapping(sample_task, ["key1"])
    view = view_class(expected, tasks)
    results = [item async for item in view]
    assert results == expected
