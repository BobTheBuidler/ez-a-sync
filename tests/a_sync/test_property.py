import pytest

from a_sync import property
from a_sync.a_sync.function import _ASyncFunction, ASyncFunction


class PropertyTester:
    def __init__(self, i: int):
        self.i = i

    @property
    async def do_stuff(self):
        return self.i


testers = [PropertyTester(i) for i in range(5)]


def test_property_descriptor_any_sync():
    assert isinstance(PropertyTester.do_stuff.any, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.any, ASyncFunction)
    assert PropertyTester.do_stuff.any.is_async_def()
    assert not PropertyTester.do_stuff.any.is_sync_default()
    assert PropertyTester.do_stuff.any(testers, sync=True) == True


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_any_async():
    assert isinstance(PropertyTester.do_stuff.any, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.any, ASyncFunction)
    assert PropertyTester.do_stuff.any.is_async_def()
    assert not PropertyTester.do_stuff.any.is_sync_default()
    assert await PropertyTester.do_stuff.any(testers, sync=False) == True


def test_property_descriptor_all_sync():
    assert isinstance(PropertyTester.do_stuff.all, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.all, ASyncFunction)
    assert PropertyTester.do_stuff.all.is_async_def()
    assert not PropertyTester.do_stuff.all.is_sync_default()
    assert PropertyTester.do_stuff.all(testers, sync=True) == False


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_all_async():
    assert isinstance(PropertyTester.do_stuff.all, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.all, ASyncFunction)
    assert PropertyTester.do_stuff.all.is_async_def()
    assert not PropertyTester.do_stuff.all.is_sync_default()
    assert await PropertyTester.do_stuff.all(testers, sync=False) == False


def test_property_descriptor_min_sync():
    assert isinstance(PropertyTester.do_stuff.min, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.min, ASyncFunction)
    assert PropertyTester.do_stuff.min.is_async_def()
    assert not PropertyTester.do_stuff.min.is_sync_default()
    assert PropertyTester.do_stuff.min(testers, sync=True) == 0


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_min_async():
    assert isinstance(PropertyTester.do_stuff.min, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.min, ASyncFunction)
    assert PropertyTester.do_stuff.min.is_async_def()
    assert not PropertyTester.do_stuff.min.is_sync_default()
    assert await PropertyTester.do_stuff.min(testers, sync=False) == 0


def test_property_descriptor_max_sync():
    assert isinstance(PropertyTester.do_stuff.max, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.max, ASyncFunction)
    assert PropertyTester.do_stuff.max.is_async_def()
    assert not PropertyTester.do_stuff.max.is_sync_default()
    assert PropertyTester.do_stuff.max(testers, sync=True) == 4


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_max_async():
    assert isinstance(PropertyTester.do_stuff.max, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.max, ASyncFunction)
    assert PropertyTester.do_stuff.max.is_async_def()
    assert not PropertyTester.do_stuff.max.is_sync_default()
    assert await PropertyTester.do_stuff.max(testers, sync=False) == 4


def test_property_descriptor_sum_sync():
    assert isinstance(PropertyTester.do_stuff.sum, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.sum, ASyncFunction)
    assert PropertyTester.do_stuff.sum.is_async_def()
    assert not PropertyTester.do_stuff.sum.is_sync_default()
    assert PropertyTester.do_stuff.sum(testers, sync=True) == 10


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_sum_async():
    assert isinstance(PropertyTester.do_stuff.sum, _ASyncFunction)
    assert isinstance(PropertyTester.do_stuff.sum, ASyncFunction)
    assert PropertyTester.do_stuff.sum.is_async_def()
    assert not PropertyTester.do_stuff.sum.is_sync_default()
    assert await PropertyTester.do_stuff.sum(testers, sync=False) == 10
