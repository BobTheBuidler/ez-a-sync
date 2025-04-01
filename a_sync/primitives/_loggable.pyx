# cython: boundscheck=False
"""
This module provides a mixin class to add debug logging capabilities to other classes.
"""

import logging
cdef object Logger = logging.Logger
cdef object getLogger = logging.getLogger
cdef object isEnabledFor = Logger.isEnabledFor
cdef object DEBUG = 10
del logging


cdef class _LoggerMixin:
    """
    A mixin class that adds logging capabilities to other classes.

    This mixin provides a cached property for accessing a logger instance and a property to check if debug logging is enabled.

    See Also:
        - :func:`logging.getLogger`
        - :class:`logging.Logger`
    """

    @property
    def logger(self) -> Logger:
        """
        Provides a logger instance specific to the class using this mixin.

        The logger ID is constructed from the module and class name, and optionally includes an instance name if available.

        Examples:
            >>> class MyClass(_LoggerMixin):
            ...     _name = "example"
            ...
            >>> instance = MyClass()
            >>> logger = instance.logger
            >>> logger.name
            'module_name.MyClass.example'

            >>> class AnotherClass(_LoggerMixin):
            ...     pass
            ...
            >>> another_instance = AnotherClass()
            >>> another_logger = another_instance.logger
            >>> another_logger.name
            'module_name.AnotherClass'

        Note:
            Replace `module_name` with the actual module name where the class is defined.

        See Also:
            - :func:`logging.getLogger`
            - :class:`logging.Logger`
        """
        return self.get_logger()
    
    cdef object get_logger(self):
        cdef object logger, cls
        cdef str cls_key, name
        logger = self._logger
        if logger is None:
            cls = type(self)
            name = getattr(self, "_name", "")
            if name:
                logger = getLogger(f"{cls.__module__}.{cls.__qualname__}.{name}")
            else:
                logger = _get_logger_for_cls(f"{cls.__module__}.{cls.__qualname__}")
            self._logger = logger
        return logger

    @property
    def debug_logs_enabled(self) -> bool:
        """
        Checks if debug logging is enabled for the logger.

        Examples:
            >>> class MyClass(_LoggerMixin):
            ...     pass
            ...
            >>> instance = MyClass()
            >>> instance.debug_logs_enabled
            False

        See Also:
            - :attr:`logging.Logger.isEnabledFor`
        """
        return isEnabledFor(self.get_logger(), DEBUG)

    cdef inline bint check_debug_logs_enabled(self):
        return isEnabledFor(self.get_logger(), DEBUG)


cdef dict[str, object] _class_loggers = {}

cdef object _get_logger_for_cls(str cls_key):
    cdef object logger = _class_loggers.get(cls_key)
    if logger is None:
        logger = getLogger(cls_key)
        _class_loggers[cls_key] = logger
    return logger

