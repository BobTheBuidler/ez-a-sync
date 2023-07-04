import asyncio
import time

import pytest

from a_sync.primitives.executor import (AsyncProcessPoolExecutor,
                                        ProcessPoolExecutor)


def do_work(i):
    time.sleep(i)
    
def test_executor():
    executor = ProcessPoolExecutor(1)
    assert isinstance(executor, AsyncProcessPoolExecutor)
    coro = executor.run(do_work, 3)
    # TODO: make `submit` return asyncio.Future
    #fut = executor.submit(do_work, 3)
    #assert isinstance(fut, asyncio.Future), fut.__dict__
    asyncio.get_event_loop().run_until_complete(coro)