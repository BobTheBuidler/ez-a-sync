from asyncio import Future
from typing import Awaitable, Iterable, NewType, TypeVar

__T = TypeVar("__T")

# We can't get this from asyncio so we make our own
_GatheringFuture = NewType("_GatheringFuture", Future[__T])

def igather(
    coros_or_futures: Iterable[Awaitable[__T]], return_exceptions: bool = False
) -> _GatheringFuture[list[__T]]: ...
