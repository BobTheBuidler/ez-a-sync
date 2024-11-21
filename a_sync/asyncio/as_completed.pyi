"""
This module extends Python's :func:`asyncio.as_completed` with additional functionality.
"""

from a_sync._typing import *

__all__ = ["as_completed"]

class tqdm_asyncio:
    @staticmethod
    def as_completed(*args, **kwargs) -> None: ...

# Names in __all__ with no definition:
#   as_completed
