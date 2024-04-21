
import asyncio
from concurrent.futures._base import Executor
from decimal import Decimal
from typing import (TYPE_CHECKING, Any, AsyncGenerator, AsyncIterable, AsyncIterator, 
                    Awaitable, Callable, Coroutine, DefaultDict, Deque, Dict, Generator, 
                    Generic, ItemsView, Iterable, Iterator, KeysView, List, Literal,
                    Mapping, NoReturn, Optional, Protocol, Set, Tuple, Type, TypedDict,
                    TypeVar, Union, ValuesView, final, overload, runtime_checkable)

from typing_extensions import Concatenate, ParamSpec, Self, Unpack


T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
I = TypeVar("I")
E = TypeVar('E', bound=Exception)
TYPE = TypeVar("TYPE", bound=Type)
P = ParamSpec("P")

Numeric = Union[int, float, Decimal]

MaybeAwaitable = Union[Awaitable[T], T]

CoroFn = Callable[P, Awaitable[T]]
SyncFn = Callable[P, T]
AnyFn = Union[CoroFn[P, T], SyncFn[P, T]]

class CoroBoundMethod(Protocol[I, P, T]):
    __self__: I
    __call__: Callable[P, Awaitable[T]]
class SyncBoundMethod(Protocol[I, P, T]):
    __self__: I
    __call__: Callable[P, T]
AnyBoundMethod = Union[CoroBoundMethod[Any, P, T], SyncBoundMethod[Any, P, T]]

@runtime_checkable
class AsyncUnboundMethod(Protocol[I, P, T]):
    __get__: Callable[[I, None], CoroBoundMethod[I, P, T]]
@runtime_checkable
class SyncUnboundMethod(Protocol[I, P, T]):
    __get__: Callable[[I, None], SyncBoundMethod[I, P, T]]
AnyUnboundMethod = Union[AsyncUnboundMethod[I, P, T], SyncUnboundMethod[I, P, T]]

AsyncGetterFunction = Callable[[I], Awaitable[T]]
SyncGetterFunction = Callable[[I], T]
AnyGetterFunction = Union[AsyncGetterFunction[I, T], SyncGetterFunction[I, T]]

AsyncDecorator = Callable[[CoroFn[P, T]], CoroFn[P, T]]
AsyncDecoratorOrCoroFn = Union[AsyncDecorator[P, T], CoroFn[P, T]]

DefaultMode = Literal['sync', 'async', None]

CacheType = Literal['memory', None]
SemaphoreSpec = Optional[Union[asyncio.Semaphore, int]]

class ModifierKwargs(TypedDict, total=False):
    default: DefaultMode
    cache_type: CacheType
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[Numeric]
    runs_per_minute: Optional[int]
    semaphore: SemaphoreSpec
    # sync modifiers
    executor: Executor

AnyIterable = Union[AsyncIterable[K], Iterable[K]]
AnyIterableOrAwaitableIterable = Union[AnyIterable[K], Awaitable[AnyIterable[K]]]