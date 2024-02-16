
import asyncio

try:
    from tqdm.asyncio import tqdm_asyncio
except ImportError as e:
    class tqdm_asyncio:  # type: ignore [no-redef]
        def as_completed(*args, **kwargs):
            raise ImportError("You must have tqdm installed to use this feature")
        
from a_sync._typing import *
from a_sync.iter import ASyncIterator

@overload
def as_completed(fs: Iterable[Awaitable[T]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: Literal[False] = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Iterator[Coroutine[None, None, T]]:
    ...
@overload
def as_completed(fs: Iterable[Awaitable[T]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: Literal[True] = True, tqdm: bool = False, **tqdm_kwargs: Any) -> ASyncIterator[T]:
    ...
@overload
def as_completed(fs: Mapping[K, Awaitable[V]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: Literal[False] = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Iterator[Coroutine[None, None, Tuple[K, V]]]:
    ...
@overload
def as_completed(fs: Mapping[K, Awaitable[V]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: Literal[True] = True, tqdm: bool = False, **tqdm_kwargs: Any) -> ASyncIterator[Tuple[K, V]]:
    ...
def as_completed(fs, *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: bool = False, tqdm: bool = False, **tqdm_kwargs: Any):
    """
    Concurrently awaits a list of awaitable objects or mappings of awaitables and returns an iterator of results.

    This function extends Python's asyncio.as_completed, providing additional features for mixed use cases of individual awaitable objects and mappings of awaitables.

    Differences from asyncio.as_completed:
    - Uses type hints for use with static type checkers.
    - Supports either individual awaitables or a k:v mapping of awaitables.
    - Can be used as an async iterator which yields the result values. Example below.
    - Provides progress reporting using tqdm if 'tqdm' is set to True.

    Args:
        fs (Iterable[Awaitable[T] or Mapping[K, Awaitable[V]]]): The awaitables to await concurrently. It can be a list of individual awaitables or a mapping of awaitables.
        timeout (float, optional): The maximum time, in seconds, to wait for the completion of awaitables. Defaults to None (no timeout).
        return_exceptions (bool, optional): If True, exceptions are returned as results instead of raising them. Defaults to False.
        aiter (bool, optional): If True, returns an async iterator of results. Defaults to False.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Returns:
        Iterator[Coroutine[None, None, T] or ASyncIterator[Tuple[K, V]]]: An iterator of results when awaiting individual awaitables or an async iterator when awaiting mappings.

    Examples:
        Awaiting individual awaitables:
        ```
        awaitables = [async_function1(), async_function2()]
        for coro in as_completed(awaitables):
            val = await coro
            ...
            
        async for val in as_completed(awaitables, aiter=True):
            ...
        ```
        
        Awaiting mappings of awaitables:
        ```
        mapping = {'key1': async_function1(), 'key2': async_function2()}
        
        for coro in as_completed(mapping):
            k, v = await coro
            ...
            
        async for k, v in as_completed(mapping, aiter=True):
            ...
        ```
    """
    if isinstance(fs, Mapping):
        return as_completed_mapping(fs, timeout=timeout, return_exceptions=return_exceptions, aiter=aiter, tqdm=tqdm, **tqdm_kwargs) 
    if return_exceptions:
        fs = [__exc_wrap(f) for f in fs]
    return (
        ASyncIterator.wrap(__yield_as_completed(fs, timeout=timeout, tqdm=tqdm, **tqdm_kwargs)) if aiter 
        else tqdm_asyncio.as_completed(fs, timeout=timeout, **tqdm_kwargs) if tqdm 
        else asyncio.as_completed(fs, timeout=timeout)
    )

@overload
def as_completed_mapping(mapping: Mapping[K, Awaitable[V]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: Literal[True] = True, tqdm: bool = False, **tqdm_kwargs: Any) -> ASyncIterator[Tuple[K, V]]:
    ...
@overload
def as_completed_mapping(mapping: Mapping[K, Awaitable[V]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: Literal[False] = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Iterator[Coroutine[None, None, Tuple[K, V]]]:
    ...
def as_completed_mapping(mapping: Mapping[K, Awaitable[V]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Union[Iterator[Coroutine[None, None, Tuple[K, V]]], ASyncIterator[Tuple[K, V]]]:
    """
    Concurrently awaits a mapping of awaitable objects and returns an iterator or async iterator of results.

    This function is designed to await a mapping of awaitable objects, where each key-value pair represents a unique awaitable. It enables concurrent execution and gathers results into an iterator or an async iterator.

    Args:
        mapping (Mapping[K, Awaitable[V]]): A dictionary-like object where keys are of type K and values are awaitable objects of type V.
        timeout (float, optional): The maximum time, in seconds, to wait for the completion of awaitables. Defaults to None (no timeout).
        return_exceptions (bool, optional): If True, exceptions are returned as results instead of raising them. Defaults to False.
        aiter (bool, optional): If True, returns an async iterator of results. Defaults to False.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Returns:
        Union[Iterator[Coroutine[None, None, Tuple[K, V]]] or ASyncIterator[Tuple[K, V]]]: An iterator of results or an async iterator when awaiting mappings.

    Example:
        ```
        mapping = {'key1': async_function1(), 'key2': async_function2()}
        
        for coro in as_completed_mapping(mapping):
            k, v = await coro
            ...
            
        async for k, v in as_completed_mapping(mapping, aiter=True):
            ...
        ```
    """
    return as_completed([__mapping_wrap(k, v, return_exceptions=return_exceptions) for k, v in mapping.items()], timeout=timeout, aiter=aiter, tqdm=tqdm, **tqdm_kwargs)

async def __yield_as_completed(futs: Iterable[Awaitable[T]], *, timeout: Optional[float] = None, return_exceptions: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> AsyncIterator[T]:
    for fut in as_completed(futs, timeout=timeout, return_exceptions=return_exceptions, tqdm=tqdm, **tqdm_kwargs):
        yield await fut

@overload
async def __mapping_wrap(k: K, v: Awaitable[V], return_exceptions: Literal[True] = True) -> Union[V, Exception]:...
@overload
async def __mapping_wrap(k: K, v: Awaitable[V], return_exceptions: Literal[False] = False) -> V:...
async def __mapping_wrap(k: K, v: Awaitable[V], return_exceptions: bool = False) -> Union[V, Exception]:
    try:
        return k, await v
    except Exception as e:
        if return_exceptions:
            return k, e
        raise e

async def __exc_wrap(awaitable: Awaitable[T]) -> Union[T, Exception]:
    try:
        return await awaitable
    except Exception as e:
        return e