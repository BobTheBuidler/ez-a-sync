import asyncio.tasks
from typing import Awaitable, Iterable, TypeVar

__T = TypeVar("__T")

def igather(
    coros_or_futures: Iterable[Awaitable[__T]], return_exceptions: bool = False
) -> asyncio.tasks._GatheringFuture[list[__T]]: ...
