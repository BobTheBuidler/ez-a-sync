# cython: boundscheck=False
import inspect
from logging import getLogger
from libc.stdint cimport uintptr_t

from a_sync._typing import *
from a_sync.a_sync._flags cimport validate_and_negate_if_necessary, validate_flag_value
from a_sync.a_sync.abstract import ASyncABC
from a_sync.a_sync.flags cimport VIABLE_FLAGS
from a_sync.exceptions import ASyncFlagException, FlagNotDefined, InvalidFlag, NoFlagsFound, TooManyFlags
from a_sync.functools cimport cached_property_unsafe


# cdef inspect
cdef object signature = inspect.signature
cdef object _empty = inspect._empty
del inspect

# cdef logging
cdef public object logger = getLogger(__name__)
cdef object _logger_is_enabled = logger.isEnabledFor
cdef object _logger_debug = logger.debug
cdef object _logger_log = logger._log
cdef object DEBUG = 10
del getLogger


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

    @classmethod  # type: ignore [misc]
    def __a_sync_default_mode__(cls) -> bint:  # type: ignore [override]
        cdef object flag
        cdef bint flag_value
        if not _logger_is_enabled(DEBUG):
            # we can optimize this if we dont need to log `flag` and the return value
            try:
                flag = _get_a_sync_flag_name_from_signature(cls, False)
                flag_value = _a_sync_flag_default_value_from_signature(cls)
            except NoFlagsFound:
                flag = _get_a_sync_flag_name_from_class_def(cls)
                flag_value = _get_a_sync_flag_value_from_class_def(cls, flag)
            return validate_and_negate_if_necessary(flag, flag_value)

        # we need an extra var so we can log it
        cdef bint sync
        
        try:
            flag = _get_a_sync_flag_name_from_signature(cls, True)
            flag_value = _a_sync_flag_default_value_from_signature(cls)
        except NoFlagsFound:
            flag = _get_a_sync_flag_name_from_class_def(cls)
            flag_value = _get_a_sync_flag_value_from_class_def(cls, flag)
        
        sync = validate_and_negate_if_necessary(flag, flag_value)
        _logger_log(
            DEBUG,
            "`%s.%s` indicates default mode is %ssynchronous",
            (cls, flag, "a" if sync is False else ""),
        )
        return sync

    def __init__(self):
        if type(self) is ASyncGenericBase:
            raise NotImplementedError(
                "You should not create instances of `ASyncGenericBase` directly, "
                "you should subclass `ASyncGenericBase` instead."
            )
        ASyncABC.__init__(self)

    @cached_property_unsafe
    def __a_sync_flag_name__(self) -> str:
        # TODO: cythonize this cache
        cdef bint debug_logs 
        if debug_logs := _logger_is_enabled(DEBUG):
            _logger_log(DEBUG, "checking a_sync flag for %s", (self, ))
        try:
            flag = _get_a_sync_flag_name_from_signature(type(self), debug_logs)
        except ASyncFlagException:
            # We can't get the flag name from the __init__ signature,
            # but maybe the implementation sets the flag somewhere else.
            # Let's check the instance's atributes
            if debug_logs:
                _logger_log(
                    DEBUG,
                    "unable to find flag name using `%s.__init__` signature, checking for flag attributes defined on %s",
                    (self.__class__.__name__, self),
                )
            present_flags = [flag for flag in VIABLE_FLAGS if hasattr(self, flag)]
            if not present_flags:
                raise NoFlagsFound(self) from None
            if len(present_flags) > 1:
                raise TooManyFlags(self, present_flags) from None
            flag = present_flags[0]
        if not isinstance(flag, str):
            raise InvalidFlag(flag)
        return flag

    @cached_property_unsafe
    def __a_sync_flag_value__(self) -> bint:
        # TODO: cythonize this cache
        """If you wish to be able to hotswap default modes, just duplicate this def as a non-cached property."""
        cdef str flag = self.__a_sync_flag_name__
        flag_value = getattr(self, flag)
        _logger_debug("`%s.%s` is currently %s", self, flag, flag_value)
        return validate_flag_value(flag, flag_value)



cdef str _get_a_sync_flag_name_from_class_def(object cls):
    _logger_debug("Searching for flags defined on %s", cls)
    try:
        return _parse_flag_name_from_list(cls, cls.__dict__)  # type: ignore [arg-type]
        # idk why __dict__ doesn't type check as a dict
    except NoFlagsFound:
        for base in cls.__bases__:
            try:
                return _parse_flag_name_from_list(cls, base.__dict__)  # type: ignore [arg-type]  idk why __dict__ doesn't type check as a dict
            except NoFlagsFound:
                pass
    raise NoFlagsFound(cls, list(cls.__dict__.keys()))


cdef bint _a_sync_flag_default_value_from_signature(object cls):
    cdef object signature = _get_init_signature(cls)
    if not _logger_is_enabled(DEBUG):
        # we can optimize this much better
        return signature.parameters[_get_a_sync_flag_name_from_signature(cls, False)].default
    
    _logger_log(
        DEBUG, "checking `__init__` signature for default %s a_sync flag value", (cls, )
    )
    cdef str flag = _get_a_sync_flag_name_from_signature(cls, True)
    cdef object flag_value = signature.parameters[flag].default
    if flag_value is _empty:  # type: ignore [attr-defined]
        raise NotImplementedError(
            "The implementation for 'cls' uses an arg to specify sync mode, instead of a kwarg. We are unable to proceed. I suppose we can extend the code to accept positional arg flags if necessary"
        )
    _logger_log(DEBUG, "%s defines %s, default value %s", (cls, flag, flag_value))
    return flag_value


cdef str _get_a_sync_flag_name_from_signature(object cls, bint debug_logs):
    if cls.__name__ == "ASyncGenericBase":
        if debug_logs:
            _logger_log(
                DEBUG, "There are no flags defined on the base class, this is expected. Skipping.", ()
            )
        return ""

    # if we fail this one there's no need to check again
    if not debug_logs:
        # we can also skip assigning params to a var
        return _parse_flag_name_from_list(cls, _get_init_signature(cls).parameters)

    _logger_log(DEBUG, "Searching for flags defined on %s.__init__", (cls, ))
    cdef object parameters = _get_init_signature(cls).parameters
    _logger_log(DEBUG, "parameters: %s", (parameters, ))
    return _parse_flag_name_from_list(cls, parameters)


cdef str _parse_flag_name_from_list(object cls, object items):
    cdef str flag
    cdef list[str] present_flags = [flag for flag in VIABLE_FLAGS if flag in items]
    if not present_flags:
        _logger_debug("There are no flags defined on %s", cls)
        raise NoFlagsFound(cls, items.keys())
    if len(present_flags) > 1:
        _logger_debug("There are too many flags defined on %s", cls)
        raise TooManyFlags(cls, present_flags)
    if _logger_is_enabled(DEBUG):
        flag = present_flags[0]
        _logger_log(DEBUG, "found flag %s", (flag, ))
        return flag
    return present_flags[0]


cdef inline bint _get_a_sync_flag_value_from_class_def(object cls, str flag):
    cdef object spec
    for spec in [cls, *cls.__bases__]:
        if flag in spec.__dict__:
            return spec.__dict__[flag]
    raise FlagNotDefined(cls, flag)


cdef dict[uintptr_t, object] _init_signature_cache = {}


cdef _get_init_signature(object cls):
    cdef uintptr_t cls_init_id = id(cls.__init__)
    init_sig = _init_signature_cache.get(cls_init_id)
    if init_sig is None:
        init_sig = signature(cls.__init__)
        _init_signature_cache[cls_init_id] = init_sig
    return init_sig
