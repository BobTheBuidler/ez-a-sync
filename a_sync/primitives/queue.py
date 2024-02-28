import asyncio
import sys

from a_sync._typing import *

if sys.version_info < (3, 9):
    class _Queue(asyncio.Queue, Generic[T]):
        __slots__ = "_maxsize", "_loop", "_getters", "_putters", "_unfinished_tasks", "_finished"
else:
    class _Queue(asyncio.Queue[T]):
        __slots__ = "_maxsize", "_getters", "_putters", "_unfinished_tasks", "_finished"

class Queue(_Queue[T]):
    # for type hint support, no functional difference
    async def get(self) -> T:
        return await super().get()
    def get_nowait(self) -> T:
        return super().get_nowait()
    async def put(self, item: T) -> None:
        return super().put(item)
    def put_nowait(self, item: T) -> None:
        return super().put_nowait(item)
    
    async def get_all(self) -> List[T]:
        """returns 1 or more items"""
        try:
            return self.get_all_nowait()
        except asyncio.QueueEmpty:
            return [await self.get()]
    def get_all_nowait(self) -> List[T]:
        """returns 1 or more items, or raises asyncio.QueueEmpty"""
        values: List[T] = []
        while True:
            try:
                values.append(self.get_nowait())
            except asyncio.QueueEmpty as e:
                if not values:
                    raise asyncio.QueueEmpty from e
                return values
            
    async def get_multi(self, i: int, can_return_less: bool = False) -> List[T]:
        _validate_args(i, can_return_less)
        items = []
        while len(items) < i and not can_return_less:
            try:
                items.extend(self.get_multi_nowait(i - len(items), can_return_less=True))
            except asyncio.QueueEmpty:
                items = [await self.get()]
        return items
    def get_multi_nowait(self, i: int, can_return_less: bool = False) -> List[T]:
        """
        Just like `asyncio.Queue.get_nowait`, but will return `i` items instead of 1.
        Set `can_return_less` to True if you want to receive up to `i` items.
        """
        _validate_args(i, can_return_less)
        items = []
        for _ in range(i):
            try:
                items.append(self.get_nowait())
            except asyncio.QueueEmpty:
                if items and can_return_less:
                    return items
                # put these back in the queue since we didn't return them
                for value in items:
                    self.put_nowait(value)
                raise asyncio.QueueEmpty from None
        return items
    
        

def _validate_args(i: int, can_return_less: bool) -> None:
    if not isinstance(i, int):
        raise TypeError(f"`i` must be an integer greater than 1. You passed {i}")
    if not isinstance(can_return_less, bool):
        raise TypeError(f"`can_return_less` must be boolean. You passed {can_return_less}")
    if i <= 1:
        raise ValueError(f"`i` must be an integer greater than 1. You passed {i}")
