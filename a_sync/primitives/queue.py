import asyncio
import sys

from a_sync._typing import *

if sys.version_info < (3, 9):
    class _Queue(asyncio.Queue, Generic[T]):...
else:
    class _Queue(asyncio.Queue[T]):...

class Queue(_Queue[T]):
    """The only difference between an a_sync.Queue and an asyncio.Queue is that `get_nowait` can retrn multiple responses."""
    @overload
    async def get(self, i: int = 1, can_return_less: bool = False) -> T:
        ...
    @overload
    async def get(self, i: int, can_return_less: bool = False) -> List[T]:
        ...
    async def get(self, i: int = 1, can_return_less: bool = False) -> Union[T, List[T]]:
        _validate_args(i, can_return_less)
        if i == 1:
            return await super().get()
        try:
            items = self.get_nowait(i, can_return_less=True)
        except asyncio.QueueEmpty:
            items = [await super().get()]
        if len(items) == i or can_return_less:
            return items
        while len(items) < i:
            items.extend(await self.get(i - len(items)))
        return items
        
    @overload
    def get_nowait(self, i: int = 1, can_return_less: bool = False) -> T:
        ...
    @overload
    def get_nowait(self, i: int, can_return_less: bool = False) -> List[T]:
        ...
    def get_nowait(self, i: int = 1, can_return_less: bool = False) -> Union[T, List[T]]:
        """
        Just like `asyncio.Queue.get_nowait`, but will return `i` items instead of 1.
        Set `can_return_less` to True if you want to receive up to `i` items.
        """
        _validate_args(i, can_return_less)
        values = []
        if i == -1:
            while True:
                try:
                    values.append(super().get_nowait())
                except asyncio.QueueEmpty:
                    return values
        for _ in range(i):
            try:
                values.append(super().get_nowait())
            except asyncio.QueueEmpty:
                if can_return_less:
                    break
                for value in values:
                    self.put_nowait(value)
                raise
        return values[0] if i == 1 else values

def _validate_args(i: int, can_return_less: bool) -> None:
    if not isinstance(i, int):
        raise TypeError(f"`i` must be a non-zero integer. You passed {i}")
    if not isinstance(can_return_less, bool):
        raise TypeError(f"`can_return_less` must be boolean. You passed {can_return_less}")
    if i == 0:
        raise ValueError(f"`i` must be a non-zero integer. You passed {i}")
    if can_return_less and i == 1:
        raise ValueError("you can't set i == 1 with can_return_less == True")