from a_sync._typing import *
from a_sync import exceptions as exceptions

def _await(awaitable: Awaitable[T]) -> T: ...
