
import asyncio
from typing import (Any, AsyncIterator, Awaitable, Iterable, Iterator, Mapping,
                    Optional, Tuple, TypeVar, Union, overload)

from tqdm.asyncio import tqdm_asyncio

from a_sync.iter import ASyncIterator

T = TypeVar('T')
KT = TypeVar('KT')
VT = TypeVar('VT')

@overload
def as_completed(fs: Mapping[KT, Awaitable[VT]], *, timeout: Optional[float], return_exceptions: bool, aiter = False, tqdm: bool, **tqdm_kwargs: Any) -> Iterator[Awaitable[Tuple[KT, VT]]]:
    ...
@overload
def as_completed(fs: Iterable[Awaitable[T]], *, timeout: Optional[float], return_exceptions: bool, aiter = False, tqdm: bool, **tqdm_kwargs: Any) -> Iterator[Awaitable[T]]:
    ...
@overload
def as_completed(fs: Mapping[KT, Awaitable[VT]], *, timeout: Optional[float], return_exceptions: bool, aiter = True, tqdm: bool, **tqdm_kwargs: Any) -> ASyncIterator[Tuple[KT, VT]]:
    ...
@overload
def as_completed(fs: Iterable[Awaitable[T]], *, timeout: Optional[float], return_exceptions: bool, aiter = True, tqdm: bool, **tqdm_kwargs: Any) -> ASyncIterator[T]:
    ...
def as_completed(fs, *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: bool = False, tqdm: bool = False, **tqdm_kwargs: Any):
    if return_exceptions:
        raise NotImplementedError
    return (
        as_completed_mapping(fs, timeout=timeout, return_exceptions=return_exceptions, aiter=aiter, tqdm=tqdm, **tqdm_kwargs) if isinstance(fs, Mapping)
        else ASyncIterator.wrap(__yield_as_completed(fs, tqdm=tqdm, **tqdm_kwargs)) if aiter 
        else tqdm_asyncio.as_completed(fs, timeout=timeout, **tqdm_kwargs) if tqdm 
        else asyncio.as_completed(fs, timeout=timeout)
    )

@overload
def as_completed_mapping(mapping: Mapping[KT, Awaitable[VT]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter = True, tqdm: bool, **tqdm_kwargs: Any) -> ASyncIterator[Tuple[KT, VT]]:
    ...
@overload
def as_completed_mapping(mapping: Mapping[KT, Awaitable[VT]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter = False, tqdm: bool, **tqdm_kwargs: Any) -> Iterator[Awaitable[Tuple[KT, VT]]]:
    ...
def as_completed_mapping(mapping: Mapping[KT, Awaitable[VT]], *, timeout: Optional[float] = None, return_exceptions: bool = False, aiter: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Union[Iterator[Awaitable[Tuple[KT, VT]]], ASyncIterator[Tuple[KT, VT]]]:
    return as_completed([__mapping_wrap(k, v) for k, v in mapping.items()], timeout=timeout, return_exceptions=return_exceptions, aiter=aiter, tqdm=tqdm, **tqdm_kwargs)

async def __yield_as_completed(futs: Iterable[Awaitable[T]], *, timeout: Optional[float] = None, return_exceptions: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> AsyncIterator[T]:
    futs = tqdm_asyncio.as_completed(futs, timeout=timeout, **tqdm_kwargs) if tqdm else asyncio.as_completed(futs, timeout=timeout)
    for fut in futs:
        yield await fut
        
async def __mapping_wrap(k: KT, v: Awaitable[VT]) -> VT:
    return k, await v
