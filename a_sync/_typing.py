
import asyncio
from concurrent.futures._base import Executor
from decimal import Decimal
from typing import (TYPE_CHECKING, Any, AsyncIterable, AsyncIterator, Awaitable, 
                    Callable, Coroutine, DefaultDict, Deque, Dict, Generator, 
                    Generic, ItemsView, Iterable, Iterator, KeysView, List, Literal,
                    Mapping, Optional, Protocol, Set, Tuple, Type, TypedDict,
                    TypeVar, Union, ValuesView, final, overload)

from typing_extensions import Concatenate, ParamSpec, Self, Unpack

if TYPE_CHECKING:
    from a_sync.abstract import ASyncABC
    ASyncInstance = TypeVar("ASyncInstance", bound=ASyncABC)
else:
    ASyncInstance = TypeVar("ASyncInstance", bound=object)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
O = TypeVar("O", bound=object)
E = TypeVar('E', bound=Exception)
P = ParamSpec("P")

Numeric = Union[int, float, Decimal]

MaybeAwaitable = Union[Awaitable[T], T]

CoroFn = Callable[P, Awaitable[T]]
SyncFn = Callable[P, T]
AnyFn = Union[CoroFn[P, T], SyncFn[P, T]]

class CoroBoundMethod(Protocol[O, P, T], Callable[P, T]):
    __self__: O
class SyncBoundMethod(Protocol[O, P, T], Callable[P, Awaitable[T]]):
    __self__: O
AnyBoundMethod = Union[CoroBoundMethod[O, P, T], SyncBoundMethod[O, P, T]]

ClassMethod = AnyFn[Concatenate[Type, P], T]

class AsyncUnboundMethod(Protocol[O, Awaitable[T], Generic[P, T]]):
    __get__: Callable[[O, None], CoroBoundMethod[O, P, T]]
class SyncUnboundMethod(Protocol[O, T]):
    __get__: Callable[[O, None], SyncBoundMethod[O, P, T]]
AnyUnboundMethod = Union[AsyncUnboundMethod[O, P, T], SyncUnboundMethod[O, P, T]]

class AsyncPropertyGetter(CoroBoundMethod[object, T]):...
class PropertyGetter(SyncBoundMethod[object, T]):...
AnyPropertyGetter = Union[AsyncPropertyGetter[T], PropertyGetter[T]]

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
