from asyncio import Future
from typing import Awaitable, Iterable, TypeAlias, TypeVar

__T = TypeVar("__T")
__TGather = TypeVar("__TGather")

# We can't get this from asyncio so we make our own
_GatheringFuture: TypeAlias = Future[__TGather]

def igather(
    coros_or_futures: Iterable[Awaitable[__T]], return_exceptions: bool = False
) -> _GatheringFuture[list[__T]]: ...
