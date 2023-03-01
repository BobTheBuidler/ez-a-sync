
import asyncio
from concurrent.futures._base import Executor
from typing import (Awaitable, Callable, Generic, Literal, Optional, TypedDict,
                    TypeVar, Union, overload)

from typing_extensions import ParamSpec, Unpack

T = TypeVar("T")
P = ParamSpec("P")

class ModifierKwargs(TypedDict, total=False):
    default: Literal['sync', 'async', None]
    cache_type: Literal['memory', None]
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[int]
    runs_per_minute: int
    semaphore: Union[int, asyncio.Semaphore]
    # sync modifiers
    executor: Executor

class Modified(Generic[T]):
    pass
