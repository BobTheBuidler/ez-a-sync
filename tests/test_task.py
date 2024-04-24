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
    assert tasks._wrapped_func is _coro_fn, f"{tasks._wrapped_func} , {_coro_fn}, {tasks._wrapped_func == _coro_fn}"
    assert tasks._wrapped_func_kwargs == {}
    assert tasks._name is None
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
    async for k in tasks.map(range(5), pop=False, yields='keys'):
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
    async for k in tasks.map(async_iter(), pop=False, yields='keys'):
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

def test_taskmapping_views_sync():
    tasks = TaskMapping(_coro_fn, range(5))
    
    # keys are currently empty until the loop has a chance to run
    assert len(tasks.keys()) == 0
    assert len(tasks.values()) == 0
    assert len(tasks.items()) == 0
    
    tasks.gather()

    assert len(tasks.keys()) == 5
    assert len(tasks.values()) == 5
    assert len(tasks.items()) == 5

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

async def _coro_fn(i: int) -> str:
    i += 1
    return str(i) * i
