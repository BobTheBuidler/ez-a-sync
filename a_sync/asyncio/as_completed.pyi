"""
This module extends Python's :func:`asyncio.as_completed` with additional functionality.
"""

from a_sync._typing import *
from a_sync.iter import ASyncIterator

__all__ = ["as_completed"]

class tqdm_asyncio:
    @staticmethod
    def as_completed(*args, **kwargs) -> None: ...

@overload
def as_completed(
    fs: Iterable[Awaitable[T]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[False] = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Iterator[Coroutine[Any, Any, T]]: ...
@overload
def as_completed(
    fs: Iterable[Awaitable[T]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[True] = True,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> ASyncIterator[T]: ...
@overload
def as_completed(
    fs: Mapping[K, Awaitable[V]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[False] = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Iterator[Coroutine[Any, Any, Tuple[K, V]]]: ...
@overload
def as_completed(
    fs: Mapping[K, Awaitable[V]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[True] = True,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> ASyncIterator[Tuple[K, V]]: ...
def as_completed(
    fs,
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: bool = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
):
    """
    Concurrently awaits a list of awaitable objects or mappings of awaitables and returns an iterator of results.

    This function extends Python's :func:`asyncio.as_completed`, providing additional features for mixed use cases of individual awaitable objects and mappings of awaitables.

    Differences from :func:`asyncio.as_completed`:
    - Uses type hints for use with static type checkers.
    - Supports either individual awaitables or a k:v mapping of awaitables.
    - Can be used as an async iterator which yields the result values using :class:`ASyncIterator`.
    - Provides progress reporting using :mod:`tqdm` if 'tqdm' is set to True.

    Note:
        The `return_exceptions` parameter is used to wrap awaitables with exceptions if set to True, allowing exceptions to be returned as results instead of being raised.

    Args:
        fs: The awaitables to await concurrently. It can be a list of individual awaitables or a mapping of awaitables.
        timeout: The maximum time, in seconds, to wait for the completion of awaitables. Defaults to None (no timeout).
        return_exceptions: If True, exceptions are wrapped and returned as results instead of raising them. Defaults to False.
        aiter: If True, returns an async iterator of results using :class:`ASyncIterator`. Defaults to False.
        tqdm: If True, enables progress reporting using :mod:`tqdm`. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for :mod:`tqdm` if progress reporting is enabled.

    Examples:
        Awaiting individual awaitables:

        >>> awaitables = [async_function1(), async_function2()]
        >>> for coro in as_completed(awaitables):
        ...     val = await coro
        ...     ...

        >>> async for val in as_completed(awaitables, aiter=True):
        ...     ...

        Awaiting mappings of awaitables:

        >>> mapping = {'key1': async_function1(), 'key2': async_function2()}
        >>> for coro in as_completed(mapping):
        ...     k, v = await coro
        ...     ...

        >>> async for k, v in as_completed(mapping, aiter=True):
        ...     ...

    See Also:
        - :func:`asyncio.as_completed`
        - :class:`ASyncIterator`
    """
