import asyncio
import pytest

from a_sync import TaskMapping, create_task, exceptions

@pytest.mark.asyncio_cooperative
async def test_create_task():
    await create_task(coro=asyncio.sleep(0), name='test')

@pytest.mark.asyncio_cooperative
async def test_persistent_task():
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
    async def task():
        return
    create_task(coro=task(), skip_gc_until_done=True)
    await asyncio.sleep(0)
    # previously, it failed here
    create_task(coro=task(), skip_gc_until_done=True)

@pytest.mark.asyncio_cooperative
async def test_task_mapping_init():
    tasks = TaskMapping(_coro_fn)
    assert tasks._wrapped_func is _coro_fn
    assert tasks._wrapped_func_kwargs == {}
    assert tasks._name == ""
    tasks = TaskMapping(_coro_fn, name='test', kwarg0=1, kwarg1=None)
    assert tasks._wrapped_func_kwargs == {'kwarg0': 1, 'kwarg1': None}
    assert tasks._name == "test"

@pytest.mark.asyncio_cooperative
async def test_task_mapping():
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
    assert await TaskMapping(_coro_fn, range(5)) == {0: "1", 1: "22", 2: "333", 3: "4444", 4: "55555"}
    assert len(tasks) == 2
    
@pytest.mark.asyncio_cooperative
async def test_task_mapping_map_with_sync_iter():
    tasks = TaskMapping(_coro_fn)
    i = 0
    async for k, v in tasks.map(range(5)):
        assert isinstance(k, int)
        assert isinstance(v, str)
        if i < 4:
            # this shouldn't work since there is a mapping in progress
            with pytest.raises(exceptions.MappingNotEmptyError):
                async for k in tasks.map(range(5)):
                    ...
        i += 1
    tasks = TaskMapping(_coro_fn)
    async for k in tasks.map(range(5), yields='keys'):
        assert isinstance(k, int)
    
@pytest.mark.asyncio_cooperative
async def test_task_mapping_map_with_async_iter():
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
            with pytest.raises(exceptions.MappingNotEmptyError):
                async for k in tasks.map(async_iter()):
                    ...
        i += 1
    tasks = TaskMapping(_coro_fn)
    async for k in tasks.map(async_iter(), yields='keys'):
        assert isinstance(k, int)

async def _coro_fn(i: int) -> str:
    i += 1
    return str(i) * i
