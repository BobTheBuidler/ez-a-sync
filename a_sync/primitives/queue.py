import asyncio
import functools
import heapq
import logging
import sys

from a_sync._task import create_task
from a_sync._typing import *

logger = logging.getLogger(__name__)

if sys.version_info < (3, 9):
    class _Queue(asyncio.Queue, Generic[T]):
        __slots__ = "_maxsize", "_loop", "_getters", "_putters", "_unfinished_tasks", "_finished"
else:
    class _Queue(asyncio.Queue[T]):
        __slots__ = "_maxsize", "_getters", "_putters", "_unfinished_tasks", "_finished"

class Queue(_Queue[T]):
    # for type hint support, no functional difference
    async def get(self) -> T:
        self._queue
        return await _Queue.get(self)
    def get_nowait(self) -> T:
        return _Queue.get_nowait(self)
    async def put(self, item: T) -> None:
        return _Queue.put(self, item)
    def put_nowait(self, item: T) -> None:
        return _Queue.put_nowait(self, item)
    
    async def get_all(self) -> List[T]:
        """returns 1 or more items"""
        try:
            return self.get_all_nowait()
        except asyncio.QueueEmpty:
            return [await self.get()]
    def get_all_nowait(self) -> List[T]:
        """returns 1 or more items, or raises asyncio.QueueEmpty"""
        values: List[T] = []
        while True:
            try:
                values.append(self.get_nowait())
            except asyncio.QueueEmpty as e:
                if not values:
                    raise asyncio.QueueEmpty from e
                return values
            
    async def get_multi(self, i: int, can_return_less: bool = False) -> List[T]:
        _validate_args(i, can_return_less)
        items = []
        while len(items) < i and not can_return_less:
            try:
                items.extend(self.get_multi_nowait(i - len(items), can_return_less=True))
            except asyncio.QueueEmpty:
                items = [await self.get()]
        return items
    def get_multi_nowait(self, i: int, can_return_less: bool = False) -> List[T]:
        """
        Just like `asyncio.Queue.get_nowait`, but will return `i` items instead of 1.
        Set `can_return_less` to True if you want to receive up to `i` items.
        """
        _validate_args(i, can_return_less)
        items = []
        for _ in range(i):
            try:
                items.append(self.get_nowait())
            except asyncio.QueueEmpty:
                if items and can_return_less:
                    return items
                # put these back in the queue since we didn't return them
                for value in items:
                    self.put_nowait(value)
                raise asyncio.QueueEmpty from None
        return items


class ProcessingQueue(_Queue[Tuple[P, "asyncio.Future[V]"]], Generic[P, V]):
    _closed: bool = False
    __slots__ = "func", "num_workers", "_worker_coro"
    def __init__(
        self, 
        func: Callable[P, Awaitable[V]], 
        num_workers: int, 
        *, 
        return_data: bool = True, 
        name: str = "",
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        if sys.version_info < (3, 10):
            super().__init__(loop=loop)
        elif loop:
            raise NotImplementedError(f"You cannot pass a value for `loop` in python {sys.version_info}")
        else:
            super().__init__()
            
        self.func = func
        self.num_workers = num_workers
        self._name = name
        self._no_futs = not return_data
        @functools.wraps(func)
        async def _worker_coro() -> NoReturn:
            # we use this little helper so we can have context of `func` in any err logs
            return await self.__worker_coro()
        self._worker_coro = _worker_coro
    def __repr__(self) -> str:
        repr_string = f"<{type(self).__name__}"
        if self._name:
            repr_string += f" name={self._name}"
        repr_string += f" func={self.func} num_workers={self.num_workers}"
        if self._unfinished_tasks:
            repr_string += f" pending={self._unfinished_tasks}"
        return f"{repr_string}>"
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[V]":
        return self.put_nowait(*args, **kwargs)
    def __del__(self) -> None:
        if self._unfinished_tasks > 0:
            context = {
                'message': f'{self} was destroyed but has work pending!',
            }
            asyncio.get_event_loop().call_exception_handler(context)
        if not self._closed:
            self.__stop_workers()
    @property
    def name(self) -> str:
        return self._name or repr(self)
    async def put(self, *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[V]":
        self._ensure_workers()
        if self._no_futs:
            return await super().put((args, kwargs))
        fut = self._create_future()
        await super().put((args, kwargs, fut))
        return fut
    def put_nowait(self, *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[V]":
        self._ensure_workers()
        if self._no_futs:
            return super().put_nowait((args, kwargs))
        fut = self._create_future()
        super().put_nowait((args, kwargs, fut))
        return fut
    async def close(self) -> None:
        self.__stop_workers()
        # let the loop run once so the tasks can be stopped fully
        await asyncio.sleep(0)
    def _create_future(self) -> "asyncio.Future[V]":
        return asyncio.get_event_loop().create_future()
    def _ensure_workers(self) -> None:
        if self._closed:
            raise RuntimeError(f"{type(self).__name__} is closed: ", self) from None
        if self._workers.done():
            worker_subtasks: List["asyncio.Task[NoReturn]"] = self._workers._workers
            for worker in worker_subtasks:
                if worker.done():
                    raise worker.exception()
            # this should never be reached, but just in case
            raise self._workers.exception()
    @functools.cached_property
    def _workers(self) -> "asyncio.Task[NoReturn]":
        logger.debug("starting worker task for %s", self)
        workers = [
            create_task(
                coro=self._worker_coro(), 
                name=f"{self.name} [Task-{i}]",
                log_destroy_pending=False,
            ) for i in range(self.num_workers)
        ]
        task = create_task(asyncio.gather(*workers), name=f"{self.name} worker main Task", log_destroy_pending=False)
        task._workers = workers
        return task
    async def __worker_coro(self) -> NoReturn:
        args: P.args
        kwargs: P.kwargs
        if self._no_futs:
            while True:
                try:
                    args, kwargs = await self.get()
                    await self.func(*args, **kwargs)
                except Exception as e:
                    logger.error("%s in worker for %s!", type(e).__name__, self)
                    logger.exception(e)
                self.task_done()
        else:
            fut: asyncio.Future[V]
            while True:
                try:
                    args, kwargs, fut = await self.get()
                    fut.set_result(await self.func(*args, **kwargs))
                except asyncio.exceptions.InvalidStateError:
                    logger.error("cannot set result for %s %s: %s", self.func.__name__, fut, result)
                except Exception as e:
                    try:
                        fut.set_exception(e)
                    except asyncio.exceptions.InvalidStateError:
                        logger.error("cannot set exception for %s %s: %s", self.func.__name__, fut, e)
                    except UnboundLocalError as u:
                        logger.error("%s for %s is broken!!!", type(self).__name__, self.func)
                        if str(e) != "local variable 'fut' referenced before assignment":
                            logger.exception(u)
                            raise u
                        logger.exception(e)
                        raise e
                self.task_done()
    def __stop_workers(self) -> None:
        self._closed = True
        # since _workers is a cached property we want to pop it from instance.__dict__ so we dont accidentally create it
        if main_worker := self.__dict__.pop("_workers", None):
            try:
                main_worker.cancel()
            except ImportError as e:
                # workers have not yet been started, and getting the property fails since
                # tasks cannot (and dont need to) be created as python is shutting down
                if str(e) == "sys.meta_path is None, Python is likely shutting down":
                    return
            for child_worker in main_worker._workers:
                child_worker.cancel()


def _validate_args(i: int, can_return_less: bool) -> None:
    if not isinstance(i, int):
        raise TypeError(f"`i` must be an integer greater than 1. You passed {i}")
    if not isinstance(can_return_less, bool):
        raise TypeError(f"`can_return_less` must be boolean. You passed {can_return_less}")
    if i <= 1:
        raise ValueError(f"`i` must be an integer greater than 1. You passed {i}")


_Args = Tuple[Any]
_Kwargs = Tuple[Tuple[str, Any]]
_Key = Tuple[_Args, _Kwargs]

class SmartFuture(asyncio.Future, Generic[T]):
    def __init__(self, queue: "SmartProcessingQueue", key: _Key, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        super().__init__(loop=loop)
        self._queue = queue
        self._key = key
        self._waiters: Set["asyncio.Task[T]"] = set()
    def __repr__(self):
        return f"<{type(self).__name__} key={self._key} waiters={self.num_waiters} {self._state}>"
    def __await__(self):
        logger.debug("entering %s", self)
        if self.done():
            return self.result()  # May raise too.
        self._asyncio_future_blocking = True
        self._waiters.add(current_task := asyncio.current_task(self._loop))
        logger.debug("awaiting %s", self)
        yield self  # This tells Task to wait for completion.
        self._waiters.remove(current_task)
        if self.num_waiters == 0:
            self._queue._futs.pop(self._key)
        if not self.done():
            raise RuntimeError("await wasn't used with future")
        return self.result()  # May raise too.
    def __lt__(self, other: "SmartFuture") -> bool:
        """heap considers lower values as higher priority so a future with more waiters will be 'less than' a future with less waiters."""
        return self.num_waiters > other.num_waiters
    @property
    def num_waiters(self) -> int:
        return len(self._waiters)


class _PriorityQueueMixin(Generic[T]):
    def _init(self, maxsize):
        self._queue: List[T] = []
    def _put(self, item, heappush=heapq.heappush):
        heappush(self._queue, item)
    def _get(self, heappop=heapq.heappop):
        return heappop(self._queue)

class PriorityProcessingQueue(_PriorityQueueMixin[T], ProcessingQueue[T, V]):
    # NOTE: WIP
    async def put(self, priority: Any, *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[V]":
        self._ensure_workers()
        fut = asyncio.get_event_loop().create_future()
        await super().put(self, (priority, args, kwargs, fut))
        return fut
    def put_nowait(self, priority: Any, *args: P.args, **kwargs: P.kwargs) -> "asyncio.Future[V]":
        self._ensure_workers()
        fut = self._create_future()
        super().put_nowait(self, (priority, args, kwargs, fut))
        return fut
    def _get(self, heappop=heapq.heappop):
        priority, args, kwargs, fut = heappop(self._queue)
        return args, kwargs, fut

class _VariablePriorityQueueMixin(_PriorityQueueMixin[T]):
    def _get(self, heapify=heapq.heapify, heappop=heapq.heappop):
        "Resort the heap to consider any changes in priorities and pop the smallest value"
        # resort the heap
        heapify(self._queue)
        # take the job with the most waiters
        return heappop(self._queue)
    def _get_key(self, *args, **kwargs) -> _Key:
        return (args, tuple((kwarg, kwargs[kwarg]) for kwarg in sorted(kwargs)))
    def _create_future(self, key: _Key) -> "asyncio.Future[V]":
        return SmartFuture(self, key, loop=asyncio.get_event_loop())

class VariablePriorityQueue(_VariablePriorityQueueMixin[T], asyncio.PriorityQueue):
    """A PriorityQueue subclass that allows priorities to be updated (or computed) on the fly"""
    # NOTE: WIP
             
class SmartProcessingQueue(_VariablePriorityQueueMixin[T], ProcessingQueue[Concatenate[T, P], V]):
    """A PriorityProcessingQueue subclass that will execute jobs with the most waiters first"""
    _no_futs = False
    def __init__(
        self, 
        func: Callable[Concatenate[T, P], Awaitable[V]], 
        num_workers: int, 
        *, 
        name: str = "",
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        super().__init__(func, num_workers, return_data=True, name=name, loop=loop)
        self._futs: Dict[_Key[T], SmartFuture[T]] = {}
    async def put(self, *args: P.args, **kwargs: P.kwargs) -> SmartFuture[V]:
        self._ensure_workers()
        key = self._get_key(*args, **kwargs)
        if fut := self._futs.get(key, None):
            return fut
        fut = self._create_future(key)
        self._futs[key] = fut
        await Queue.put(self, (fut, args, kwargs))
        return fut
    def put_nowait(self, *args: P.args, **kwargs: P.kwargs) -> SmartFuture[V]:
        self._ensure_workers()
        key = self._get_key(*args, **kwargs)
        if fut := self._futs.get(key, None):
            return fut
        fut = self._create_future(key)
        self._futs[key] = fut
        Queue.put_nowait(self, (fut, args, kwargs))
        return fut
    def _get(self):
        fut, args, kwargs = super()._get()
        return args, kwargs, fut
    async def __worker_coro(self) -> NoReturn:
        args: P.args
        kwargs: P.kwargs
        fut: SmartFuture[V]
        while True:
            try:
                args, kwargs, fut = await self.get()
                logger.debug("processing %s", fut)
                result = await self.func(*args, **kwargs)
                fut.set_result(result)
            except asyncio.exceptions.InvalidStateError:
                logger.error("cannot set result for %s %s: %s", self.func.__name__, fut, result)
            except Exception as e:
                logger.debug("%s: %s", type(e).__name__, e)
                try:
                    fut.set_exception(e)
                except asyncio.exceptions.InvalidStateError:
                    logger.error("cannot set exception for %s %s: %s", self.func.__name__, fut, e)
                except UnboundLocalError as u:
                    logger.error("%s for %s is broken!!!", type(self).__name__, self.func)
                    if str(e) != "local variable 'fut' referenced before assignment":
                        logger.exception(u)
                        raise u
                    logger.exception(e)
                    raise e
            self.task_done()
