from typing import Awaitable, Iterable, List, TypeVar

__T = TypeVar("__T")

def igather(
    coros_or_futures: Iterable[Awaitable[__T]], return_exceptions: bool = False
) -> Awaitable[List[__T]]: ...
