import asyncio
from typing import (Any, AsyncIterator, Awaitable, Dict, Iterable, Iterator,
                    Mapping, Optional, Tuple, TypeVar, Union, overload)

from tqdm.asyncio import tqdm_asyncio
from typing_extensions import ParamSpec

from a_sync.iter import ASyncIterator
from a_sync.utils.iterators import (as_yielded, exhaust_iterator,
                                    exhaust_iterators)

T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")
P = ParamSpec("P")

__all__ = [
    "all",
    "any",
    "as_yielded",
]

async def any(*awaitables) -> bool:
    futs = [asyncio.ensure_future(a) for a in awaitables]
    for fut in asyncio.as_completed(futs):
        if bool(await fut):
            for fut in futs:
                fut.cancel()
            return True
    return False
    
async def all(*awaitables) -> bool:
    futs = [asyncio.ensure_future(a) for a in awaitables]
    for fut in asyncio.as_completed(awaitables):
        if not bool(await fut):
            for fut in futs:
                fut.cancel()
            return False
    return True

async def gather_mapping(mapping: Mapping[KT, Awaitable[VT]], tqdm: bool = False, **tqdm_kwargs: Any) -> Dict[KT, VT]:
    results = {k: None for k in mapping.keys()}  # return data in same order
    async for k, v in as_completed_mapping(mapping, tqdm=tqdm, **tqdm_kwargs):
        results[k] = v
    return results

def as_completed(fs: Iterable[Awaitable[T]], *, timeout: Optional[float] = None, aiter: bool = False, tqdm: bool = False, **tqdm_kwargs: Any):
    return (
        as_completed_mapping(fs) if isinstance(fs, Mapping)
        else ASyncIterator.wrap(__yield_as_completed(fs, tqdm=tqdm, **tqdm_kwargs)) if aiter 
        else tqdm_asyncio.as_completed(fs, timeout=timeout, **tqdm_kwargs) if tqdm 
        else asyncio.as_completed(fs, timeout=timeout)
    )

@overload
def as_completed_mapping(mapping: Mapping[KT, Awaitable[VT]], *, timeout: Optional[float] = None, aiter = True, tqdm: bool, **tqdm_kwargs: Any) -> ASyncIterator[Tuple[KT, VT]]:...
@overload
def as_completed_mapping(mapping: Mapping[KT, Awaitable[VT]], *, timeout: Optional[float] = None, aiter = False, tqdm: bool, **tqdm_kwargs: Any) -> Iterator[Awaitable[Tuple[KT, VT]]]:...
def as_completed_mapping(mapping: Mapping[KT, Awaitable[VT]], *, timeout: Optional[float] = None, aiter: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Union[Iterator[Awaitable[Tuple[KT, VT]]], ASyncIterator[Tuple[KT, VT]]]:
    return as_completed([__mapping_wrap(k, v) for k, v in mapping.items()], timeout=timeout, aiter=aiter, tqdm=tqdm, **tqdm_kwargs)

async def __yield_as_completed(futs: Iterable[Awaitable[T]], *, timeout: Optional[float] = None, tqdm: bool = False, **tqdm_kwargs: Any) -> AsyncIterator[T]:
    if tqdm:
        for fut in tqdm_asyncio.as_completed(futs, timeout=timeout, **tqdm_kwargs):
            yield await fut
    else:
        for fut in asyncio.as_completed(futs, timeout=timeout):
            yield await fut
        
async def __mapping_wrap(k: KT, v: Awaitable[VT]) -> VT:
    return k, await v

    