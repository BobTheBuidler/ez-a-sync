"""
This module provides a mixin class to add debug logging capabilities to other classes.
"""

from functools import cached_property
from logging import Logger, getLogger, DEBUG


class _LoggerMixin:
    """
    A mixin class that adds logging capabilities to other classes.

    This mixin provides a cached property for accessing a logger instance and a property to check if debug logging is enabled.
    """

    @cached_property
    def logger(self) -> Logger:
        """
        Returns a logger instance specific to the class using this mixin.

        The logger ID is constructed from the module and class name, and optionally includes an instance name if available.

        Returns:
            Logger: A logger instance for the class.
        """
        logger_id = type(self).__qualname__
        if hasattr(self, "_name") and self._name:
            logger_id += f".{self._name}"
        return getLogger(logger_id)

    @property
    def debug_logs_enabled(self) -> bool:
        """
        Checks if debug logging is enabled for the logger.

        Returns:
            bool: True if debug logging is enabled, False otherwise.
        """
        return self.logger.isEnabledFor(DEBUG)
