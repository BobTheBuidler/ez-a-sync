
import asyncio
from concurrent.futures._base import Executor
from typing import (TYPE_CHECKING, Any, Awaitable, Callable, DefaultDict, Dict,
                    Generic, Iterator, List, Literal, Optional, Tuple,
                    Type, TypedDict, TypeVar, Union, overload)

from typing_extensions import Concatenate, ParamSpec, Unpack

if TYPE_CHECKING:
    from a_sync.abstract import ASyncABC

T = TypeVar("T")
P = ParamSpec("P")

MaybeAwaitable = Union[Awaitable[T], T]

Property = Callable[["ASyncABC"], T]
HiddenMethod = Callable[["ASyncABC", Dict[str, bool]], T]
AsyncBoundMethod = Callable[Concatenate["ASyncABC", P], Awaitable[T]]
BoundMethod = Callable[Concatenate["ASyncABC", P], T]

CoroFn = Callable[P, Awaitable[T]]
SyncFn = Callable[P, T]
AnyFn = Union[CoroFn[P, T], SyncFn[P, T]]

AsyncDecorator = Callable[[CoroFn[P, T]], CoroFn[P, T]]

AllToAsyncDecorator = Callable[[AnyFn[P, T]], CoroFn[P, T]]
AllToSyncDecorator = Callable[[AnyFn[P, T]], SyncFn[P, T]]

AsyncDecoratorOrCoroFn = Union[AsyncDecorator[P, T], CoroFn[P, T]]

DefaultMode = Literal['sync', 'async', None]

CacheType = Literal['memory', None]
SemaphoreSpec = Optional[Union[asyncio.Semaphore, int]]

class ModifierKwargs(TypedDict, total=False):
    default: DefaultMode
    cache_type: CacheType
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[int]
    runs_per_minute: Optional[int]
    semaphore: SemaphoreSpec
    # sync modifiers
    executor: Executor
