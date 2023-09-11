
"""
While not the focus of this lib, this module includes some new primitives and some modified versions of standard asyncio primitives.
"""

from a_sync.primitives.executor import (AsyncProcessPoolExecutor,
                                        AsyncThreadPoolExecutor,
                                        ProcessPoolExecutor,
                                        PruningThreadPoolExecutor,
                                        ThreadPoolExecutor)
from a_sync.primitives.locks import *
from a_sync.primitives.queue import Queue
