
import asyncio

import a_sync

@a_sync.a_sync
async def some_test_fn() -> int:
    return 2

def test_decorator():
    assert asyncio.get_event_loop().run_until_complete(some_test_fn()) == 2
    assert some_test_fn(sync=True) == 2
    assert some_test_fn(asynchronous=False) == 2
