import pytest

from a_sync import property


class PropertyTester:
    def __init__(self, i: int):
        self.i = i

    @property
    async def do_stuff(self):
        return self.i


testers = [PropertyTester(i) for i in range(5)]


def test_property_descriptor_any_sync():
    assert PropertyTester.do_stuff.any(testers, sync=True) == True


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_any_async():
    assert await PropertyTester.do_stuff.any(testers, sync=False) == True


def test_property_descriptor_all_sync():
    assert PropertyTester.do_stuff.all(testers, sync=True) == False


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_all_async():
    assert await PropertyTester.do_stuff.all(testers, sync=False) == False


def test_property_descriptor_min_sync():
    assert PropertyTester.do_stuff.min(testers, sync=True) == 0


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_min_async():
    assert await PropertyTester.do_stuff.min(testers, sync=False) == 0


def test_property_descriptor_max_sync():
    assert PropertyTester.do_stuff.max(testers, sync=True) == 4


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_max_async():
    assert await PropertyTester.do_stuff.max(testers, sync=False) == 4


def test_property_descriptor_sum_sync():
    assert PropertyTester.do_stuff.sum(testers, sync=True) == 10


@pytest.mark.asyncio_cooperative
async def test_property_descriptor_sum_async():
    assert await PropertyTester.do_stuff.sum(testers, sync=False) == 10
