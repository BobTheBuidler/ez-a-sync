"""
This module provides utility functions for handling asynchronous operations.

It contains two helper functions:

    get_event_loop:
        Retrieves the current event loop, creating one if none exists.
        
    _await:
        Awaits an awaitable and returns its completed result.

Note:
    This module does NOT convert synchronous functions to asynchronous ones.

Examples:
    Getting the current event loop:
    
        >>> from a_sync.a_sync._helpers import get_event_loop
        >>> import asyncio
        >>> loop = get_event_loop()
        >>> isinstance(loop, asyncio.AbstractEventLoop)
        True

    Awaiting an awaitable:
    
        >>> from a_sync.a_sync._helpers import _await
        >>> import asyncio
        >>>
        >>> async def example_coro():
        ...     return 42
        >>>
        >>> result = _await(example_coro())
        >>> result
        42

See Also:
    :func:`asyncio.get_event_loop` for the built-in implementation.
"""

from a_sync._typing import *
from a_sync import exceptions as exceptions

def get_event_loop() -> asyncio.AbstractEventLoop: ...
def _await(awaitable: Awaitable[T]) -> T: ...