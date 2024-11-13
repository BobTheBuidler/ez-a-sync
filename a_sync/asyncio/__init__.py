"""
This package provides custom utilities and extensions to the builtin `asyncio` package.

These utilities include enhanced versions of common asyncio functions, offering additional
features and improved functionality for asynchronous programming.
"""

from a_sync.asyncio.as_completed import as_completed
from a_sync.asyncio.create_task import create_task
from a_sync.asyncio.gather import gather
from a_sync.asyncio.utils import get_event_loop

__all__ = ["create_task", "gather", "as_completed", "get_event_loop"]
