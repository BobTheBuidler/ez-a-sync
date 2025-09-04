import asyncio
import atexit
import signal
import time

import pytest

from a_sync import ProcessPoolExecutor, ThreadPoolExecutor, PruningThreadPoolExecutor
from a_sync.executor import (
    _EXECUTORS,
    _shutdown_all_executors,
)


class DummyExecutor:
    def __init__(self):
        self.shutdown_called = False

    def shutdown(self, wait=True):
        self.shutdown_called = True


@pytest.mark.asyncio_cooperative
async def test_process_pool_executor_run():
    """Test the :class:`ProcessPoolExecutor` by running and submitting the work function asynchronously.

    This test ensures that the :meth:`~ProcessPoolExecutor.run` method of the
    :class:`~ProcessPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~ProcessPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = ProcessPoolExecutor(1)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio_cooperative
async def test_thread_pool_executor_run():
    """Test the :class:`ThreadPoolExecutor` by running and submitting the work function asynchronously.

    This test ensures that the :meth:`~ThreadPoolExecutor.run` method of the
    :class:`~ThreadPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~ThreadPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = ThreadPoolExecutor(1)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio_cooperative
async def test_pruning_thread_pool_executor_run():
    """Test the :class:`PruningThreadPoolExecutor` by running and submitting the work function asynchronously.

    This test ensures that the :meth:`~PruningThreadPoolExecutor.run` method of the
    :class:`~PruningThreadPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~PruningThreadPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = PruningThreadPoolExecutor(1)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio_cooperative
async def test_process_pool_executor_submit():
    """Test the :class:`ProcessPoolExecutor` by submitting the work function.

    This test ensures that the :meth:`~ProcessPoolExecutor.submit` method of the
    :class:`~ProcessPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~ProcessPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~ProcessPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = ProcessPoolExecutor(1)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio_cooperative
async def test_thread_pool_executor_submit():
    """Test the :class:`ThreadPoolExecutor` by submitting the work function.

    This test ensures that the :meth:`~ThreadPoolExecutor.submit` method of the
    :class:`~ThreadPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~ThreadPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~ThreadPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = ThreadPoolExecutor(1)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio_cooperative
async def test_pruning_thread_pool_executor_submit():
    """Test the :class:`PruningThreadPoolExecutor` by submitting the work function.

    This test ensures that the :meth:`~PruningThreadPoolExecutor.submit` method of the
    :class:`~PruningThreadPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~PruningThreadPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~PruningThreadPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = PruningThreadPoolExecutor(1)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio_cooperative
async def test_process_pool_executor_sync_run():
    """Test the :class:`ProcessPoolExecutor` by running and submitting the work function synchronously.

    This test ensures that the :meth:`~ProcessPoolExecutor.run` method of the
    :class:`~ProcessPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~ProcessPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = ProcessPoolExecutor(0)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio_cooperative
async def test_thread_pool_executor_sync_run():
    """Test the :class:`ThreadPoolExecutor` by running and submitting the work function synchronously.

    This test ensures that the :meth:`~ThreadPoolExecutor.run` method of the
    :class:`~ThreadPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~ThreadPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = ThreadPoolExecutor(0)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio_cooperative
async def test_pruning_thread_pool_executor_sync_run():
    """Test the :class:`PruningThreadPoolExecutor` by running and submitting the work function synchronously.

    This test ensures that the :meth:`~PruningThreadPoolExecutor.run` method of the
    :class:`~PruningThreadPoolExecutor` returns a coroutine when executed with a synchronous function.

    See Also:
        - :meth:`~PruningThreadPoolExecutor.run`
        - :func:`asyncio.iscoroutine`
    """
    executor = PruningThreadPoolExecutor(0)
    coro = executor.run(time.sleep, 0.1)
    assert asyncio.iscoroutine(coro)
    await coro


@pytest.mark.asyncio_cooperative
async def test_process_pool_executor_sync_submit():
    """Test the :class:`ProcessPoolExecutor` by submitting the work function synchronously.

    This test ensures that the :meth:`~ProcessPoolExecutor.submit` method of the
    :class:`~ProcessPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~ProcessPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~ProcessPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = ProcessPoolExecutor(0)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio_cooperative
async def test_thread_pool_executor_sync_submit():
    """Test the :class:`ThreadPoolExecutor` by submitting the work function synchronously.

    This test ensures that the :meth:`~ThreadPoolExecutor.submit` method of the
    :class:`~ThreadPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~ThreadPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~ThreadPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = ThreadPoolExecutor(0)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


@pytest.mark.asyncio_cooperative
async def test_pruning_thread_pool_executor_sync_submit():
    """Test the :class:`PruningThreadPoolExecutor` by submitting the work function synchronously.

    This test ensures that the :meth:`~PruningThreadPoolExecutor.submit` method of the
    :class:`~PruningThreadPoolExecutor` returns an :class:`asyncio.Future` when executed with a synchronous function.

    Note:
        The :meth:`~PruningThreadPoolExecutor.submit` method in this context returns an :class:`asyncio.Future`,
        not a :class:`concurrent.futures.Future`. This is specific to the implementation of the executors
        in the `a_sync` library, which adapts the behavior to integrate with the asyncio event loop.

    See Also:
        - :meth:`~PruningThreadPoolExecutor.submit`
        - :class:`asyncio.Future`
    """
    executor = PruningThreadPoolExecutor(0)
    fut = executor.submit(time.sleep, 0.1)
    assert isinstance(fut, asyncio.Future)
    await fut


def test_executor_registration_and_shutdown(monkeypatch):
    """
    Test that executors are registered and shutdown is called on all of them.
    """
    dummy1 = DummyExecutor()
    dummy2 = DummyExecutor()
    _EXECUTORS.clear()
    from a_sync.executor import register_executor

    register_executor(dummy1)
    register_executor(dummy2)
    assert dummy1 in _EXECUTORS
    assert dummy2 in _EXECUTORS
    _shutdown_all_executors()
    assert dummy1.shutdown_called
    assert dummy2.shutdown_called


def test_signal_and_atexit_registration(monkeypatch):
    """
    Test that signal handlers and atexit are registered and chainable.
    """
    called = {"atexit": False, "sigint": False, "sigterm": False}

    def fake_atexit(func):
        called["atexit"] = True
        return func

    def fake_signal(sig, handler):
        if sig == signal.SIGINT:
            called["sigint"] = True
        elif sig == signal.SIGTERM:
            called["sigterm"] = True
        return handler

    monkeypatch.setattr(atexit, "register", fake_atexit)
    monkeypatch.setattr(signal, "signal", fake_signal)
    # Re-register handlers with monkeypatched functions
    from a_sync.executor import _register_executor_shutdown as reg

    reg()
    assert called["atexit"]
    assert called["sigint"]
    assert called["sigterm"]


def test_multiple_executor_shutdown(monkeypatch):
    """
    Test that all registered executors are shut down, even if one raises.
    """

    class FailingExecutor:
        def __init__(self):
            self.shutdown_called = False

        def shutdown(self, wait=True):
            self.shutdown_called = True
            raise RuntimeError("fail")

    dummy = DummyExecutor()
    failing = FailingExecutor()
    _EXECUTORS.clear()
    from a_sync.executor import register_executor

    register_executor(dummy)
    register_executor(failing)
    # Should not raise
    _shutdown_all_executors()
    assert dummy.shutdown_called
    assert failing.shutdown_called


def test_real_executor_registration():
    """
    Test that real executors are registered and can be shut down.
    """
    _EXECUTORS.clear()
    tpe = ThreadPoolExecutor(max_workers=1)
    ppe = ProcessPoolExecutor(max_workers=1)
    pe = PruningThreadPoolExecutor(max_workers=1)
    assert tpe in _EXECUTORS
    assert ppe in _EXECUTORS
    assert pe in _EXECUTORS
    _shutdown_all_executors()
    # No exceptions should be raised
