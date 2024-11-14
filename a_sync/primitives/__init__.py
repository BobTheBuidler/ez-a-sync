"""
This module includes both new primitives and modified versions of standard asyncio primitives.

The primitives provided in this module are:
- :class:`~a_sync.primitives.locks.Semaphore`
- :class:`~a_sync.primitives.locks.PrioritySemaphore`
- :class:`~a_sync.primitives.ThreadsafeSemaphore`
- :class:`~a_sync.primitives.locks.CounterLock`
- :class:`~a_sync.primitives.locks.Event`
- :class:`~a_sync.primitives.queue.Queue`
- :class:`~a_sync.primitives.queue.ProcessingQueue`
- :class:`~a_sync.primitives.queue.SmartProcessingQueue`
 
 These primitives extend or modify the functionality of standard asyncio primitives to provide additional features or improved performance for specific use cases.

Examples:
    Using a Semaphore to limit concurrent access:

    >>> from a_sync.primitives.locks import Semaphore
    >>> semaphore = Semaphore(2)
    >>> async with semaphore:
    ...     # perform some operation
    ...     pass

    Using a Queue to manage tasks:

    >>> from a_sync.primitives.queue import Queue
    >>> queue = Queue()
    >>> await queue.put('task1')
    >>> task = await queue.get()
    >>> print(task)
    task1

See Also:
    - :mod:`asyncio` for standard asyncio primitives.
    - :mod:`a_sync.primitives.locks` for lock-related primitives.
    - :mod:`a_sync.primitives.queue` for queue-related primitives.

"""

from a_sync.primitives.locks import *
from a_sync.primitives.queue import Queue, ProcessingQueue, SmartProcessingQueue

__all__ = [
    "Semaphore",
    "ThreadsafeSemaphore",
    "PrioritySemaphore",
    "CounterLock",
    "Event",
    "Queue",
    "ProcessingQueue",
    "SmartProcessingQueue",
]
