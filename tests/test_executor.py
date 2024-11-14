import asyncio
import time

import pytest

from a_sync.executor import AsyncProcessPoolExecutor, ProcessPoolExecutor


def do_work(i, kwarg=None):
    """Performs work by sleeping for a specified duration.

    Args:
        i (int): The duration to sleep.
        kwarg (optional): An optional keyword argument to assert against `i`.

    Raises:
        AssertionError: If `kwarg` is provided and does not equal `i`.
    """
    time.sleep(i)
    if kwarg:
        assert kwarg == i


def test_executor():
    """Tests the functionality of the ProcessPoolExecutor.

    This test verifies that the ProcessPoolExecutor behaves as expected,
    including running tasks, handling futures, and managing exceptions.

    Note:
        `ProcessPoolExecutor` is an alias for `AsyncProcessPoolExecutor`, 
        which is why the assertion `assert isinstance(executor, AsyncProcessPoolExecutor)` is always true.

    See Also:
        - :class:`a_sync.executor.AsyncProcessPoolExecutor`
        - :meth:`a_sync.executor._AsyncExecutorMixin.run`
        - :meth:`a_sync.executor._AsyncExecutorMixin.submit`
    """
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

    asyncio.get_event_loop().run_until_complete(executor.run(do_work, 3, kwarg=3))
    asyncio.get_event_loop().run_until_complete(fut)
