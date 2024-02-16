
import asyncio
import logging

from a_sync._typing import *
from a_sync import exceptions
from a_sync.iter import ASyncIterable
from a_sync.utils.as_completed import as_completed
from a_sync.utils.gather import gather
from a_sync.utils.iterators import as_yielded, exhaust_iterator


logger = logging.getLogger(__name__)

def create_task(coro: Awaitable[T], *, name: Optional[str] = None, skip_gc_until_done: bool = False) -> "asyncio.Task[T]":
    """A wrapper over `asyncio.create_task` which will work with any `Awaitable` object, not just `Coroutine` objects"""
    if not asyncio.iscoroutine(coro):
        coro = __await(coro)
    task = asyncio.create_task(coro, name=name)
    if skip_gc_until_done:
        __persist(asyncio.create_task(__persisted_task_exc_wrap(task)))
    return task


MappingFn = Callable[Concatenate[K, P], Awaitable[V]]

class TaskMapping(ASyncIterable[Tuple[K, V]], DefaultDict[K, "asyncio.Task[V]"]):
    def __init__(self, coro_fn: MappingFn[K, P, V] = None, *iterables: AnyIterable[K], name: str = '', **coro_fn_kwargs: P.kwargs) -> None:
        self._coro_fn = coro_fn
        self._coro_fn_kwargs = coro_fn_kwargs
        self._name = name
        self._loader: Optional["asyncio.Task[None]"]
        if iterables:
            self._loader = create_task(exhaust_iterator(self._tasks_for_iterables(*iterables)))
        else:
            self._loader = None
    def __setitem__(self, item: Any, value: Any) -> None:
        raise NotImplementedError("You cannot manually set items in a TaskMapping")
    def __getitem__(self, item: K) -> "asyncio.Task[V]":
        try:
            return super().__getitem__(item)
        except KeyError:
            task = create_task(
                coro=self._coro_fn(item, **self._coro_fn_kwargs),
                name=f"{self._name}[{item}]" if self._name else f"{item}",
            )
            super().__setitem__(item, task)
            return task
    def __await__(self) -> Generator[Any, None, Dict[K, V]]:
        """await all tasks and returns a mapping with the results for each key"""
        return self._await().__await__()
    async def __aiter__(self) -> AsyncIterator[Tuple[K, V]]:
        """aiterate thru all key-task pairs, yielding the key-result pair as each task completes"""
        yielded = set()
        # if you inited the TaskMapping with some iterators, we will load those
        if self._loader:
            while not self._loader.done():
                async for key, value in self.yield_completed(pop=False):
                    if key not in yielded:
                        yield _yield(key, value, "both")
                        yielded.add(key)
                await asyncio.sleep(0)
            # loader is already done by this point, but we need to check for exceptions
            await self._loader
        elif not self:
            # if you didn't init the TaskMapping with iterators and you didn't start any tasks manually, we should fail
            raise exceptions.MappingIsEmptyError
        # if there are any tasks that still need to complete, we need to await them and yield them
        if self:
            async for key, value in as_completed(self, aiter=True):
                if key not in yielded:
                    yield _yield(key, value, "both")
    #def keys(self) -> KeysView[K]:
    #    if self._loader and not self._loader.done():
    #        raise RuntimeError("the loader needs time to complete. bob will figure out a way to make this not impact sync users")
    #    return super().keys()
    async def map(self, *iterables: AnyIterable[K], pop: bool = True, yields: Literal['keys', 'both'] = 'both') -> AsyncIterator[Tuple[K, V]]:
        if self:
            raise exceptions.MappingNotEmptyError
        else:
            logger.info(self)
        async for _ in self._tasks_for_iterables(*iterables):
            async for key, value in self.yield_completed(pop=pop):
                yield _yield(key, value, yields)
        async for key, value in as_completed(self, aiter=True):
            if pop:
                self.pop(key)
            yield _yield(key, value, yields)
    async def yield_completed(self, pop: bool = True) -> AsyncIterator[Tuple[K, V]]:
        for k, task in dict(self).items():
            if task.done():
                if pop:
                    task = self.pop(k)
                yield k, await task
    async def _await(self) -> Dict[K, V]:
        if self._loader:
            await self._loader
        if not self:
            raise exceptions.MappingIsEmptyError
        return await gather(self)
    async def _tasks_for_iterables(self, *iterables) -> AsyncIterator["asyncio.Task[V]"]:
        async for key in as_yielded(*[_yield_keys(iterable) for iterable in iterables]):  # type: ignore [attr-defined]
            yield self[key]  # ensure task is running
        

__persisted_tasks: Set["asyncio.Task[Any]"] = set()

async def __await(awaitable: Awaitable[T]) -> T:
    return await awaitable
    
def __persist(task: "asyncio.Task[Any]") -> None:
    __persisted_tasks.add(task)
    __prune_persisted_tasks()

def __prune_persisted_tasks():
    for task in tuple(__persisted_tasks):
        if task.done():
            if e := task.exception() and not isinstance(e, exceptions.PersistedTaskException):
                logger.exception(e)
                raise e
            __persisted_tasks.discard(task)

async def __persisted_task_exc_wrap(task: "asyncio.Task[T]") -> T:
    try:
        await task
    except Exception as e:
        raise exceptions.PersistedTaskException(e, task) from e

@overload
def _yield(key: K, value: V, yields: Literal['keys']) -> K:...
@overload
def _yield(key: K, value: V, yields: Literal['both']) -> Tuple[K, V]:...
def _yield(key: K, value: V, yields: Literal['keys', 'both']) -> Union[K, Tuple[K, V]]:
    if yields == 'both':
        return key, value
    elif yields == 'keys':
        return key
    else:
        raise ValueError(f"`yields` must be 'keys' or 'both'. You passed {yields}")

async def _yield_keys(iterable: AnyIterable[K]) -> AsyncIterator[K]:
    if isinstance(iterable, AsyncIterable):
        async for key in iterable:
            yield key
    elif isinstance(iterable, Iterable):
        for key in iterable:
            yield key
    else:
        raise TypeError(iterable)
