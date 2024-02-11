
from a_sync._typing import *
from a_sync.iter import ASyncIterator

MappingFn = Callable[Concatenate[K, P], Awaitable[V]]

@overload
def map(coro_fn: MappingFn[K, P, V], *iterables: AnyIterable[K], yields: Literal['keys'], **coro_fn_kwargs: P.kwargs) -> ASyncIterator[K]:...
@overload
def map(coro_fn: MappingFn[K, P, V], *iterables: AnyIterable[K], yields: Literal['both'], **coro_fn_kwargs: P.kwargs) -> ASyncIterator[Tuple[K, V]]:...
def map(coro_fn: MappingFn[K, P, V], *iterables: AnyIterable[K], yields: Literal['keys', 'both'] = 'both', **coro_fn_kwargs: P.kwargs) -> Union[ASyncIterator[K], ASyncIterator[Tuple[K, V]]]:
    from a_sync.task import TaskMapping
    return ASyncIterator.wrap(TaskMapping(coro_fn, **coro_fn_kwargs).map(*iterables, yields=yields))