"""
This module includes both new primitives and modified versions of standard asyncio primitives.

The primitives provided in this module are:

- Semaphore
- ThreadsafeSemaphore
- PrioritySemaphore
- CounterLock
- Event
- Queue
- ProcessingQueue
- SmartProcessingQueue

These primitives extend or modify the functionality of standard asyncio primitives to provide additional features or improved performance for specific use cases.
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
