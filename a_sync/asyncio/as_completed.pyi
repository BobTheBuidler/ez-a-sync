"""
This module extends Python's :func:`asyncio.as_completed` with additional functionality.
"""

from collections.abc import Awaitable, Coroutine, Iterable, Iterator, Mapping
from typing import Any, Literal, overload

from a_sync._typing import K, T, V
from a_sync.iter import ASyncIterator

__all__ = ["as_completed"]

class tqdm_asyncio:
    @staticmethod
    def as_completed(*args, **kwargs) -> None: ...

@overload
def as_completed(
    fs: Iterable[Awaitable[T]],
    *,
    timeout: float | None = None,
    return_exceptions: bool = False,
    aiter: Literal[False] = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Iterator[Coroutine[Any, Any, T]]:
    """Yield coroutines as awaitables complete (sync iterator)."""
    ...
@overload
def as_completed(
    fs: Iterable[Awaitable[T]],
    *,
    timeout: float | None = None,
    return_exceptions: bool = False,
    aiter: Literal[True] = True,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> ASyncIterator[T]:
    """Yield values as awaitables complete (async iterator)."""
    ...
@overload
def as_completed(
    fs: Mapping[K, Awaitable[V]],
    *,
    timeout: float | None = None,
    return_exceptions: bool = False,
    aiter: Literal[False] = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Iterator[Coroutine[Any, Any, tuple[K, V]]]:
    """Yield key/value coroutines as awaitables complete (sync iterator)."""
    ...
@overload
def as_completed(
    fs: Mapping[K, Awaitable[V]],
    *,
    timeout: float | None = None,
    return_exceptions: bool = False,
    aiter: Literal[True] = True,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> ASyncIterator[tuple[K, V]]:
    """Yield key/value results as awaitables complete (async iterator)."""
    ...
