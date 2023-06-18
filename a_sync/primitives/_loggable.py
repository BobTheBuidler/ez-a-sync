
from functools import cached_property
from logging import Logger, getLogger


class _Loggable:
    @cached_property
    def logger(self) -> Logger:
        return getLogger(f"a_sync.{self.__class__.__name__}")