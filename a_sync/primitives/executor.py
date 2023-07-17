
"""
With these executors, you can simply run sync fns in your executor with `await executor.run(fn, *args)`

`executor.submit(fn, *args)` will work the same as the concurrent.futures implementation, but will return an asyncio.Future instead of a concurrent.futures.Future
"""

import asyncio
import concurrent.futures as cf
import multiprocessing.context
import queue
import threading
import weakref
from concurrent.futures import _base, thread
from functools import cached_property
from typing import Any, Callable, Optional, Tuple, TypeVar

from typing_extensions import ParamSpec

from a_sync.primitives._debug import _DebugDaemonMixin

TEN_MINUTES = 60 * 10

T = TypeVar('T')
P = ParamSpec('P')


class _AsyncExecutorMixin(cf.Executor, _DebugDaemonMixin):
    _max_workers: int
    _workers: str
    async def run(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """
        A shorthand way to call `await asyncio.get_event_loop().run_in_executor(this_executor, fn, *args)`
        Doesn't `await this_executor.run(fn, *args)` look so much better?
        
        Oh, and you can also use kwargs!
        """
        return fn(*args, **kwargs) if self.sync_mode else await self.submit(fn, *args, **kwargs)
    def submit(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[T]":
        """Submits a job to the executor and returns an `asyncio.Future` that can be awaited for the result without blocking."""
        if self.sync_mode:
            fut = asyncio.ensure_future(self._exec_sync(fn, *args, **kwargs))
        else:
            fut = asyncio.futures.wrap_future(super().submit(fn, *args, **kwargs))
            self._start_debug_daemon(fut, fn, *args, **kwargs)
        return fut
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} object at {hex(id(self))} [{self.worker_count_current}/{self._max_workers} {self._workers}]>"
    def __len__(self) -> int:
        # NOTE: should this be queue length instead? probably
        return self.worker_count_current
    @cached_property
    def sync_mode(self) -> bool:
        return self._max_workers == 0
    @property
    def worker_count_current(self) -> int:
        len(getattr(self, f"_{self._workers}"))
    async def _exec_sync(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Just wraps a fn and its args into an awaitable."""
        return fn(*args, **kwargs)
    async def _debug_daemon(self, fut: asyncio.Future, fn, *args, **kwargs) -> None:
        """Runs until manually cancelled by the finished work item"""
        while not fut.done():
            await asyncio.sleep(15)
            if not fut.done():
                self.logger.debug(f'{self} processing {fn}{args}{kwargs}')
    
# Process

class AsyncProcessPoolExecutor(_AsyncExecutorMixin, cf.ProcessPoolExecutor):
    _workers = "processes"
    def __init__(
        self, 
        max_workers: Optional[int] = None, 
        mp_context: Optional[multiprocessing.context.BaseContext] = None, 
        initializer: Callable[..., object] = None,
        initargs: Tuple[Any, ...] = (),
    ) -> None:
        if max_workers == 0:
            super().__init__(1, mp_context, initializer, initargs)
            self._max_workers = 0
        else:
            super().__init__(max_workers, mp_context, initializer, initargs)

# Thread

class AsyncThreadPoolExecutor(_AsyncExecutorMixin, cf.ThreadPoolExecutor):
    _workers = "threads"
    def __init__(
        self, 
        max_workers: Optional[int] = None, 
        thread_name_prefix: str = '', 
        initializer: Callable[..., object] = None,
        initargs: Tuple[Any, ...] = (),
    ) -> None:
        if max_workers == 0:
            super().__init__(1, thread_name_prefix, initializer, initargs)
            self._max_workers = 0
        else:
            super().__init__(max_workers, thread_name_prefix, initializer, initargs)
    
# For backward-compatibility
ProcessPoolExecutor = AsyncProcessPoolExecutor
ThreadPoolExecutor = AsyncThreadPoolExecutor

# Pruning thread pool

def _worker(executor_reference, work_queue, initializer, initargs, timeout):  # NOTE: NEW 'timeout'
    if initializer is not None:
        try:
            initializer(*initargs)
        except BaseException:
            _base.LOGGER.critical('Exception in initializer:', exc_info=True)
            executor = executor_reference()
            if executor is not None:
                executor._initializer_failed()
            return
        
    try:
        while True:
            try:  # NOTE: NEW
                work_item = work_queue.get(block=True, 
                                           timeout=timeout)  # NOTE: NEW
            except queue.Empty:  # NOTE: NEW
                # Its been 'timeout' seconds and there are no new work items.  # NOTE: NEW
                # Let's suicide the thread.  # NOTE: NEW
                executor = executor_reference()  # NOTE: NEW
                
                with executor._adjusting_lock:  # NOTE: NEW
                    # NOTE: We keep a minimum of one thread active to prevent locks
                    if len(executor) > 1:  # NOTE: NEW
                        t = threading.current_thread()  # NOTE: NEW
                        executor._threads.remove(t)  # NOTE: NEW
                        thread._threads_queues.pop(t)  # NOTE: NEW
                        # Let the executor know we have one less idle thread available
                        executor._idle_semaphore.acquire(blocking=False)  # NOTE: NEW
                        return  # NOTE: NEW 
                continue
                
            if work_item is not None:
                work_item.run()
                # Delete references to object. See issue16284
                del work_item

                # attempt to increment idle count
                executor = executor_reference()
                if executor is not None:
                    executor._idle_semaphore.release()
                del executor
                continue

            executor = executor_reference()
            # Exit if:
            #   - The interpreter is shutting down OR
            #   - The executor that owns the worker has been collected OR
            #   - The executor that owns the worker has been shutdown OR
            if thread._shutdown or executor is None or executor._shutdown:
                # Flag the executor as shutting down as early as possible if it
                # is not gc-ed yet.
                if executor is not None:
                    executor._shutdown = True
                # Notice other workers
                work_queue.put(None)
                return
            del executor
    except BaseException:
        _base.LOGGER.critical('Exception in worker', exc_info=True)

class PruningThreadPoolExecutor(AsyncThreadPoolExecutor):
    """
    This ThreadPoolExecutor implementation prunes inactive threads after 'timeout' seconds without a work item.
    Pruned threads will be automatically recreated as needed for future workloads. up to 'max_threads' can be active at any one time.
    """
    def __init__(self, max_workers=None, thread_name_prefix='',
                 initializer=None, initargs=(), timeout=TEN_MINUTES):
        self._timeout=timeout
        self._adjusting_lock = threading.Lock()
        super().__init__(max_workers, thread_name_prefix, initializer, initargs)
    
    def __len__(self) -> int:
        return len(self._threads)
        
    def _adjust_thread_count(self):
        with self._adjusting_lock:
            # if idle threads are available, don't spin new threads
            if self._idle_semaphore.acquire(timeout=0):
                return

            # When the executor gets lost, the weakref callback will wake up
            # the worker threads.
            def weakref_cb(_, q=self._work_queue):
                q.put(None)

            num_threads = len(self._threads)
            if num_threads < self._max_workers:
                thread_name = '%s_%d' % (self._thread_name_prefix or self,
                                         num_threads)
                t = threading.Thread(name=thread_name, target=_worker,
                                     args=(weakref.ref(self, weakref_cb),
                                           self._work_queue,
                                           self._initializer,
                                           self._initargs,
                                           self._timeout))
                t.daemon = True
                t.start()
                self._threads.add(t)
                thread._threads_queues[t] = self._work_queue

executor = PruningThreadPoolExecutor(128)
