
from a_sync import aliases
from a_sync.base import ASyncGenericBase
from a_sync.decorator import a_sync
from a_sync.semaphores import (DummySemaphore, ThreadsafeSemaphore,
                               apply_semaphore)
from a_sync.singleton import ASyncGenericSingleton

# I alias the aliases for your convenience.
# I prefer "aka" but its meaning is not intuitive when reading code so I created both aliases for you to choose from.
# NOTE: Overkill? Maybe.
aka = alias = aliases

# alias for backward-compatability, will be removed eventually, probably in 0.1.0
ASyncBase = ASyncGenericBase    

