
"""
While not the focus of this lib, this module includes some new primitives and some modified versions of standard asyncio primitives.
"""

from a_sync.primitives.executor import (ProcessPoolExecutor,
                                        PruningThreadPoolExecutor,
                                        ThreadPoolExecutor)
from a_sync.primitives.locks import *
