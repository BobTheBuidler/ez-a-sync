import asyncio
import sys

from a_sync._typing import *

if sys.version_info < (3, 9):
    bases = (asyncio.Queue, Generic[T])
else:
    bases = (asyncio.Queue[T], )

class Queue(*bases):
    """The only difference between an a_sync.Queue and an asyncio.Queue is that `get_nowait` can retrn multiple responses."""
    @overload
    def get_nowait(self, i = 1, can_return_less: bool = False) -> T:
        ...
    @overload
    def get_nowait(self, i: int, can_return_less: bool = False) -> List[T]:
        ...
    def get_nowait(self, i: int = 1, can_return_less: bool = False) -> Union[T, List[T]]:
        """
        Just like `asyncio.Queue.get_nowait`, but will return `i` items instead of 1.
        Set `can_return_less` to True if you want to receive up to `i` items.
        """
        if can_return_less and i == 1:
            raise ValueError("you cant set i == 1 with can_return_less == True")
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
                raise
        return values[0] if i == 1 else values