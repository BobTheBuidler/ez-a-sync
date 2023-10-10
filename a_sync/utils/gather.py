
import asyncio
from typing import (Any, Awaitable, Dict, List, Mapping, TypeVar, Union,
                    overload)

from tqdm.asyncio import tqdm_asyncio

from a_sync.utils.as_completed import as_completed_mapping

T = TypeVar('T')
KT = TypeVar('KT')
VT = TypeVar('VT')

@overload
async def gather(*awaitables: Mapping[KT, Awaitable[VT]], return_exceptions: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Dict[KT, VT]:
    ...
@overload
async def gather(*awaitables: Awaitable[T], return_exceptions: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> List[T]:
    ...
async def gather(*awaitables: Union[Awaitable[T], Mapping[KT, Awaitable[VT]]], return_exceptions: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Union[List[T], Dict[KT, VT]]:
    return await (
        gather_mapping(awaitables[0], return_exceptions=return_exceptions, tqdm=tqdm, **tqdm_kwargs) if _is_mapping(awaitables)
        else tqdm_asyncio.gather(*awaitables, return_exceptions=return_exceptions, **tqdm_kwargs) if tqdm
        else asyncio.gather(*awaitables, return_exceptions=return_exceptions)
    )
    
async def gather_mapping(mapping: Mapping[KT, Awaitable[VT]], return_exceptions: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Dict[KT, VT]:
    results = {k: None for k in mapping.keys()}  # return data in same order
    async for k, v in as_completed_mapping(mapping, return_exceptions=return_exceptions, aiter=True, tqdm=tqdm, **tqdm_kwargs):
        results[k] = v
    return results

_is_mapping = lambda awaitables: len(awaitables) == 1 and isinstance(awaitables[0], Mapping)
