
from typing import Awaitable, Callable, Literal, Tuple, Union, overload

from a_sync._typing import K, P, V, AnyIterable
from a_sync.iter import ASyncIterator


@overload
def map(coro_fn: Callable[P, Awaitable[V]], *iterables: AnyIterable[P.args], yields: Literal['keys'], **coro_fn_kwargs: P.kwargs) -> ASyncIterator[K]:...
@overload
def map(coro_fn: Callable[P, Awaitable[V]], *iterables: AnyIterable[P.args], yields: Literal['both'], **coro_fn_kwargs: P.kwargs) -> ASyncIterator[Tuple[K, V]]:...
def map(coro_fn: Callable[P, Awaitable[V]], *iterables: AnyIterable[P.args], yields: Literal['keys', 'both'] = 'both', **coro_fn_kwargs: P.kwargs) -> Union[ASyncIterator[K], ASyncIterator[Tuple[K, V]]]:
    from a_sync.task import TaskMapping
    return ASyncIterator.wrap(TaskMapping(coro_fn, **coro_fn_kwargs).map(*iterables, yields=yields))