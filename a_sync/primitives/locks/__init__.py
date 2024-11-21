from a_sync.primitives.locks.counter import CounterLock
from a_sync.primitives.locks.event import CythonEvent as Event
from a_sync.primitives.locks.semaphore import (
    DummySemaphore,
    Semaphore,
    ThreadsafeSemaphore,
)
from a_sync.primitives.locks.prio_semaphore import PrioritySemaphore
