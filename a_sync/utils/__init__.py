import asyncio
from typing import Awaitable, Dict, Iterator, Mapping, Tuple, TypeVar, List, Callable
from typing_extensions import ParamSpec
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

async def gather_mapping(mapping: Mapping[KT, Awaitable[VT]]) -> Dict[KT, VT]:
    results = {k: None for k in mapping.keys()}  # return data in same order
    async for k, v in as_completed_mapping(mapping):
        results[k] = v
    return results

def as_completed_mapping(mapping: Mapping[KT, Awaitable[VT]]) -> Iterator["asyncio.Task[Tuple[KT, VT]]"]:
    return asyncio.as_completed([__as_completed_wrap(k, v) for k, v in mapping.items()])

async def __as_completed_wrap(k: KT, v: Awaitable[VT]) -> VT:
    return k, await v

    