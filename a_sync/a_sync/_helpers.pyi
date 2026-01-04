"""
This module provides utility functions for handling asynchronous operations
and converting synchronous functions to asynchronous ones.
"""

import asyncio

from a_sync import exceptions as exceptions
from a_sync._typing import Awaitable, T

def get_event_loop() -> asyncio.AbstractEventLoop: ...
def _await(awaitable: Awaitable[T]) -> T: ...
