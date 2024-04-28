
"""
While not the focus of this lib, this module includes some new primitives and some modified versions of standard asyncio primitives.
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
