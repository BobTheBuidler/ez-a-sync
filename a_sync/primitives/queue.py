import asyncio
import sys
from typing import Generic, TypeVar

T = TypeVar('T')

if sys.version_info < (3, 9):
    bases = (asyncio.Queue, Generic[T])
else:
    bases = (asyncio.Queue[T], )

class Queue(*bases):
    """The only difference between an a_sync.Queue and an asyncio.Queue is that `get_nowait` can retrn multiple responses."""
    def get_nowait(self, i: int = 1, can_return_less: bool = False) -> T:
        """
        Just like `asyncio.Queue.get_nowait`, but will return `i` items instead of 1.
        Set `can_return_less` to True if you want to receive up to `i` items.
        """
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
        return values