import functools
import inspect
import logging
from contextlib import suppress

from a_sync import exceptions
from a_sync._typing import *
from a_sync.a_sync._flags cimport negate_if_necessary
from a_sync.a_sync.abstract import ASyncABC
from a_sync.a_sync.flags import VIABLE_FLAGS


logger = logging.getLogger(__name__)

cdef object c_logger = logger


class ASyncGenericBase(ASyncABC):
    """
    Base class for creating dual-function sync/async-capable classes without writing all your code twice.

    This class, via its inherited metaclass :class:`~ASyncMeta', provides the foundation for creating hybrid sync/async classes. It allows methods
    and properties to be defined once and used in both synchronous and asynchronous contexts.

    The class uses the :func:`a_sync` decorator internally to create dual-mode methods and properties.
    Subclasses should define their methods as coroutines (using `async def`) where possible, and
    use the `@a_sync.property` or `@a_sync.cached_property` decorators for properties that need to support both modes.

    Example:
        ```python
        class MyClass(ASyncGenericBase):
            def __init__(self, sync: bool):
                self.sync = sync

            @a_sync.property
            async def my_property(self):
                return await some_async_operation()

            @a_sync
            async def my_method(self):
                return await another_async_operation()

        # Synchronous usage
        obj = MyClass(sync=True)
        sync_result = obj.my_property
        sync_method_result = obj.my_method()

        # Asynchronous usage
        obj = MyClass(sync=False)
        async_result = await obj.my_property
        async_method_result = await obj.my_method()
        ```

    Note:
        When subclassing, be aware that all async methods and properties will be
        automatically wrapped to support both sync and async calls. This allows for
        seamless usage in different contexts without changing the underlying implementation.
    """

    def __init__(self):
        cdef str cls_name
        if type(self) is ASyncGenericBase:
            cls_name = type(self).__name__
            raise NotImplementedError(
                f"You should not create instances of `{cls_name}` directly, you should subclass `ASyncGenericBase` instead."
            )
        ASyncABC.__init__(self)

    @functools.cached_property
    def __a_sync_flag_name__(self) -> str:
        # TODO: cythonize this cache
        c_logger.debug("checking a_sync flag for %s", self)
        try:
            flag = _get_a_sync_flag_name_from_signature(type(self))
        except exceptions.ASyncFlagException:
            # We can't get the flag name from the __init__ signature,
            # but maybe the implementation sets the flag somewhere else.
            # Let's check the instance's atributes
            c_logger.debug(
                "unable to find flag name using `%s.__init__` signature, checking for flag attributes defined on %s",
                self.__class__.__name__,
                self,
            )
            present_flags = [flag for flag in VIABLE_FLAGS if hasattr(self, flag)]
            if not present_flags:
                raise exceptions.NoFlagsFound(self) from None
            if len(present_flags) > 1:
                raise exceptions.TooManyFlags(self, present_flags) from None
            flag = present_flags[0]
        if not isinstance(flag, str):
            raise exceptions.InvalidFlag(flag)
        return flag

    @functools.cached_property
    def __a_sync_flag_value__(self) -> bool:
        # TODO: cythonize this cache
        """If you wish to be able to hotswap default modes, just duplicate this def as a non-cached property."""
        if c_logger.isEnabledFor(logging.DEBUG):
            flag = self.__a_sync_flag_name__
            flag_value = getattr(self, flag)
            c_logger._log(logging.DEBUG, "`%s.%s` is currently %s", self, flag, flag_value)

        else:
            flag_value = getattr(self, self.__a_sync_flag_name__)

        if not isinstance(flag_value, bool):
            raise exceptions.InvalidFlagValue(flag, flag_value)

        return flag_value

    @classmethod  # type: ignore [misc]
    def __a_sync_default_mode__(cls) -> bint:  # type: ignore [override]
        cdef object flag
        cdef bint flag_value
        if not c_logger.isEnabledFor(logging.DEBUG):
            # we can optimize this if we dont need to log `flag` and the return value
            try:
                flag = _get_a_sync_flag_name_from_signature(cls)
                flag_value = _a_sync_flag_default_value_from_signature(cls)
            except exceptions.NoFlagsFound:
                flag = _get_a_sync_flag_name_from_class_def(cls)
                flag_value = _get_a_sync_flag_value_from_class_def(cls, flag)
            try:
                return negate_if_necessary(flag, flag_value)  # type: ignore [arg-type]
            except TypeError as e:
                raise exceptions.InvalidFlagValue(flag, flag_value) from e.__cause__

        # we need an extra var so we can log it
        cdef bint sync
        
        try:
            flag = _get_a_sync_flag_name_from_signature(cls)
            flag_value = _a_sync_flag_default_value_from_signature(cls)
        except exceptions.NoFlagsFound:
            flag = _get_a_sync_flag_name_from_class_def(cls)
            flag_value = _get_a_sync_flag_value_from_class_def(cls, flag)
        
        try:
            sync = negate_if_necessary(flag, flag_value)  # type: ignore [arg-type]
        except TypeError as e:
            raise exceptions.InvalidFlagValue(flag, flag_value) from e.__cause__

        c_logger._log(
            logging.DEBUG,
            "`%s.%s` indicates default mode is %ssynchronous",
            cls,
            flag,
            "a" if sync is False else "",
        )
        return sync



cdef str _get_a_sync_flag_name_from_class_def(object cls):
    c_logger.debug("Searching for flags defined on %s", cls)
    try:
        return _parse_flag_name_from_list(cls, cls.__dict__)  # type: ignore [arg-type]
        # idk why __dict__ doesn't type check as a dict
    except exceptions.NoFlagsFound:
        for base in cls.__bases__:
            with suppress(exceptions.NoFlagsFound):
                return _parse_flag_name_from_list(cls, base.__dict__)  # type: ignore [arg-type]
                # idk why __dict__ doesn't type check as a dict
    raise exceptions.NoFlagsFound(cls, list(cls.__dict__.keys()))


cdef bint _a_sync_flag_default_value_from_signature(object cls):
    cdef object signature = inspect.signature(cls.__init__)
    if not c_logger.isEnabledFor(logging.DEBUG):
        # we can optimize this much better
        return signature.parameters[_get_a_sync_flag_name_from_signature(cls)].default
    
    c_logger._log(
        logging.DEBUG, "checking `__init__` signature for default %s a_sync flag value", cls
    )
    cdef str flag = _get_a_sync_flag_name_from_signature(cls)
    cdef object flag_value = signature.parameters[flag].default
    if flag_value is inspect._empty:  # type: ignore [attr-defined]
        raise NotImplementedError(
            "The implementation for 'cls' uses an arg to specify sync mode, instead of a kwarg. We are unable to proceed. I suppose we can extend the code to accept positional arg flags if necessary"
        )
    c_logger._log(logging.DEBUG, "%s defines %s, default value %s", cls, flag, flag_value)
    return flag_value


cdef str _get_a_sync_flag_name_from_signature(object cls):
    if cls.__name__ == "ASyncGenericBase":
        c_logger.debug(
            "There are no flags defined on the base class, this is expected. Skipping."
        )
        return None

    # if we fail this one there's no need to check again
    if not c_logger.isEnabledFor(logging.DEBUG):
        # we can also skip assigning params to a var
        return _parse_flag_name_from_list(cls, inspect.signature(cls.__init__).parameters)

    c_logger._log(logging.DEBUG, "Searching for flags defined on %s.__init__", cls)
    cdef object parameters = inspect.signature(cls.__init__).parameters
    c_logger._log(logging.DEBUG, "parameters: %s", parameters)
    return _parse_flag_name_from_list(cls, parameters)


cdef str _parse_flag_name_from_list(object cls, object items):
    cdef list[str] present_flags
    cdef str flag
    present_flags = [flag for flag in VIABLE_FLAGS if flag in items]
    if not present_flags:
        c_logger.debug("There are too many flags defined on %s", cls)
        raise exceptions.NoFlagsFound(cls, items.keys())
    if len(present_flags) > 1:
        c_logger.debug("There are too many flags defined on %s", cls)
        raise exceptions.TooManyFlags(cls, present_flags)
    if c_logger.isEnabledFor(logging.DEBUG):
        flag = present_flags[0]
        c_logger._log(logging.DEBUG, "found flag %s", flag)
        return flag
    else:
        return present_flags[0]


cdef bint _get_a_sync_flag_value_from_class_def(object cls, str flag):
    cdef object spec
    for spec in [cls, *cls.__bases__]:
        if flag in spec.__dict__:
            return spec.__dict__[flag]
    raise exceptions.FlagNotDefined(cls, flag)
