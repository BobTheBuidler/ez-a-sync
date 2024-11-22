"""
This module provides utility functions for handling asynchronous operations
and converting synchronous functions to asynchronous ones.
"""

from a_sync._typing import *
from a_sync import exceptions as exceptions

def get_event_loop() -> asyncio.AbstractEventLoop: ...
def _await(awaitable: Awaitable[T]) -> T: ...
