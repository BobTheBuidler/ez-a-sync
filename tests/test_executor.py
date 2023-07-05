import asyncio
import time

import pytest

from a_sync.primitives.executor import (AsyncProcessPoolExecutor,
                                        ProcessPoolExecutor)


def do_work(i, kwarg=None):
    time.sleep(i)
    if kwarg:
        assert kwarg == i
    
def test_executor():
    executor = ProcessPoolExecutor(1)
    assert isinstance(executor, AsyncProcessPoolExecutor)
    coro = executor.run(do_work, 3)
    # TODO: make `submit` return asyncio.Future
    asyncio.get_event_loop().run_until_complete(coro)
    fut = executor.submit(do_work, 3)
    assert isinstance(fut, asyncio.Future), fut.__dict__
    asyncio.get_event_loop().run_until_complete(fut)
    
    # asyncio implementation cant handle kwargs :(
    with pytest.raises(TypeError):
        asyncio.get_event_loop().run_until_complete(
            asyncio.get_event_loop().run_in_executor(executor, do_work, 3, kwarg=3)
        )
        
    # but our clean implementation can :)
    fut = executor.submit(do_work, 3, kwarg=3)
    
    asyncio.get_event_loop().run_until_complete(
        executor.run(do_work, 3, kwarg=3)
    )
    asyncio.get_event_loop().run_until_complete(
        fut
    )
    