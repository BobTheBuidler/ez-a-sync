"""
This module provides a mixin class to add debug logging capabilities to other classes.
"""

from logging import Logger, getLogger, DEBUG


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
        cdef str logger_id
        cdef object logger, cls
        logger = self._logger
        if not logger:
            cls = type(self)
            logger_id = "{}.{}".format(cls.__module__, cls.__qualname__)
            if hasattr(self, "_name") and self._name:
                logger_id += ".{}".format(self._name)
            logger = getLogger(logger_id)
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
        return self.get_logger().isEnabledFor(DEBUG)

    cdef bint check_debug_logs_enabled(self):
        return self.get_logger().isEnabledFor(DEBUG)
