
from functools import cached_property
from logging import Logger, getLogger, DEBUG


class _LoggerMixin:
    @cached_property
    def logger(self) -> Logger:
        logger_id = f"{self.__class__.__module__}.{self.__class__.__name__}"
        if hasattr(self, '_name') and self._name:
            logger_id += f'.{self._name}'
        return getLogger(logger_id)
    @property
    def debug_logs_enabled(self) -> bool:
        return self.logger.isEnabledFor(DEBUG)
