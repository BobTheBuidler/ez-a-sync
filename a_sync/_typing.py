
import asyncio
from concurrent.futures._base import Executor
from typing import (TYPE_CHECKING, Awaitable, Callable, DefaultDict, Dict,
                    Generic, Literal, Optional, Tuple, TypedDict, TypeVar,
                    Union, overload)

from typing_extensions import Concatenate, ParamSpec, Unpack

T = TypeVar("T")
P = ParamSpec("P")

DefaultMode = Literal['sync', 'async', None]

SemaphoreSpec = Optional[Union[asyncio.Semaphore, int]]

class ModifierKwargs(TypedDict, total=False):
    default: DefaultMode
    cache_type: Literal['memory', None]
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[int]
    runs_per_minute: Optional[int]
    semaphore: SemaphoreSpec
    # sync modifiers
    executor: Executor

class Modified(Generic[T]):
    pass
