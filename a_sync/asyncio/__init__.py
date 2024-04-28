"""
This package contains buffed versions of the objects found in the builtin `asyncio` package.
"""

from a_sync.asyncio.as_completed import as_completed
from a_sync.asyncio.create_task import create_task
from a_sync.asyncio.gather import gather

__all__ = ["create_task", "gather", "as_completed"]
