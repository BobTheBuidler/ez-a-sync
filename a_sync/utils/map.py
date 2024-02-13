
from a_sync._typing import *

MappingFn = Callable[Concatenate[K, P], Awaitable[V]]

def map(coro_fn: MappingFn[K, P, V], *iterables: AnyIterable[K], **coro_fn_kwargs: P.kwargs) -> TaskMapping[K, V]:
    from a_sync.task import TaskMapping
    return TaskMapping(coro_fn, *iterables, **coro_fn_kwargs)
