# cython: boundscheck=False
import inspect
from logging import getLogger

from cpython.object cimport Py_TYPE, PyObject
from cpython.tuple cimport PyTuple_GET_SIZE, PyTuple_GetItem

from a_sync._typing import *
from a_sync.a_sync._flags cimport validate_and_negate_if_necessary, validate_flag_value
from a_sync.a_sync.abstract import ASyncABC
from a_sync.a_sync.flags cimport VIABLE_FLAGS
from a_sync.exceptions import ASyncFlagException, FlagNotDefined, InvalidFlag, NoFlagsFound, TooManyFlags
from a_sync.functools cimport cached_property_unsafe


cdef extern from "Python.h":
    ctypedef struct PyTypeObject:
        PyObject *tp_bases
        PyObject *tp_dict

ctypedef object object_id
ctypedef dict[str, object] cls_init_flags


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


cdef object _init_ASyncABC = ASyncABC.__init__


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
        cdef str flag
        cdef bint flag_value
        cdef PyTypeObject *cls_ptr
        
        cls_ptr = <PyTypeObject*>cls
        if not _logger_is_enabled(DEBUG):
            # we can optimize this if we dont need to log `flag` and the return value
            try:
                flag = _get_a_sync_flag_name_from_signature(cls_ptr, False)
                flag_value = _a_sync_flag_default_value_from_signature(cls_ptr)
            except NoFlagsFound:
                flag = _get_a_sync_flag_name_from_class_def(cls_ptr)
                flag_value = _get_a_sync_flag_value_from_class_def(cls, flag)
            return validate_and_negate_if_necessary(flag, flag_value)
        
        try:
            flag = _get_a_sync_flag_name_from_signature(cls_ptr, True)
            flag_value = _a_sync_flag_default_value_from_signature(cls_ptr)
        except NoFlagsFound:
            flag = _get_a_sync_flag_name_from_class_def(cls_ptr)
            flag_value = _get_a_sync_flag_value_from_class_def(cls, flag)
        
        cdef bint sync = validate_and_negate_if_necessary(flag, flag_value)
        _logger_log(
            DEBUG,
            "`%s.%s` indicates default mode is %ssynchronous",
            (cls, flag, "a" if sync is False else ""),
        )
        return sync

    def __init__(self):
        if Py_TYPE(self) == ASyncGenericBase_ptr:
            raise NotImplementedError(
                "You should not create instances of `ASyncGenericBase` directly, "
                "you should subclass `ASyncGenericBase` instead."
            )
        _init_ASyncABC(self)

    @cached_property_unsafe
    def __a_sync_flag_name__(self) -> str:
        # TODO: cythonize this cache
        cdef bint debug_logs 
        if debug_logs := _logger_is_enabled(DEBUG):
            _logger_log(DEBUG, "checking a_sync flag for %s", (self, ))
        try:
            flag = _get_a_sync_flag_name_from_signature(Py_TYPE(self), debug_logs)
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


cdef PyTypeObject *ASyncGenericBase_ptr = <PyTypeObject*>ASyncGenericBase


cdef inline str _get_a_sync_flag_name_from_class_def(PyTypeObject *cls_ptr):
    cdef object bases
    cdef PyObject *bases_ptr
    cdef PyTypeObject *base_ptr
    cdef Py_ssize_t len_bases

    if _logger_is_enabled(DEBUG):
        _logger_log(DEBUG, "Searching for flags defined on %s", (<object>cls_ptr,))

    try:
        return _parse_flag_name_from_dict_keys(cls_ptr, <object>cls_ptr.tp_dict)
    except NoFlagsFound:
        bases_ptr = cls_ptr.tp_bases  # This is a tuple or NULL
        if bases_ptr != NULL:
            bases = <object>bases_ptr
            len_bases = PyTuple_GET_SIZE(bases)
            for i in range(len_bases):
                base_ptr = <PyTypeObject*>PyTuple_GetItem(bases, i)
                try:
                    return _get_a_sync_flag_name_from_class_def(base_ptr)
                except NoFlagsFound:
                    pass
    raise NoFlagsFound(<object>cls_ptr, list(<object>cls_ptr.tp_dict))


cdef bint _a_sync_flag_default_value_from_signature(PyTypeObject *cls_ptr):
    cdef cls_init_flags flags = _get_init_flags(cls_ptr)
    
    if not _logger_is_enabled(DEBUG):
        # we can optimize this much better
        return flags[_get_a_sync_flag_name_from_signature(cls_ptr, False)].default
    
    cdef object cls = <object>cls_ptr
    _logger_log(
        DEBUG, "checking `__init__` signature for default %s a_sync flag value", (cls, )
    )
    
    cdef str flag = _get_a_sync_flag_name_from_signature(cls_ptr, True)
    cdef object flag_value = flags[flag].default
    if flag_value is _empty:  # type: ignore [attr-defined]
        raise NotImplementedError(
            "The implementation for 'cls' uses an arg to specify sync mode, instead of a kwarg. We are unable to proceed. I suppose we can extend the code to accept positional arg flags if necessary"
        )
    _logger_log(DEBUG, "%s defines %s, default value %s", (cls, flag, flag_value))
    return flag_value


cdef str _get_a_sync_flag_name_from_signature(PyTypeObject *cls_ptr, bint debug_logs):
    cdef cls_init_flags flags
    
    if cls_ptr == ASyncGenericBase_ptr:
        # There are no flags defined on the base class
        return ""
    
    # if we fail this one there's no need to check again
    if not debug_logs:
        # we can also skip assigning params to a var
        return _parse_flag_name_from_dict_keys(cls_ptr, _get_init_flags(cls_ptr))

    _logger_log(DEBUG, "Searching for flags defined on %s.__init__", (<object>cls_ptr, ))
    flags = _get_init_flags(cls_ptr)
    _logger_log(DEBUG, "flags: %s", (flags, ))
    return _parse_flag_name_from_dict_keys(cls_ptr, flags)


cdef inline str _parse_flag_name_from_dict_keys(PyTypeObject *cls_ptr, dict[str, object] d):
    cdef str flag
    cdef list[str] present_flags = [flag for flag in VIABLE_FLAGS if flag in d]
    cdef int flags_len = len(present_flags)
    if not flags_len:
        cls = <object>cls_ptr
        _logger_debug("There are no flags defined on %s", cls)
        raise NoFlagsFound(cls, d.keys())
    if flags_len > 1:
        cls = <object>cls_ptr
        _logger_debug("There are too many flags defined on %s", cls)
        raise TooManyFlags(cls, present_flags)
    if _logger_is_enabled(DEBUG):
        flag = present_flags[0]
        _logger_log(DEBUG, "found flag %s", (flag, ))
        return flag
    return present_flags[0]


cdef inline bint _get_a_sync_flag_value_from_class_def(object cls, str flag):
    cdef object spec
    cdef bint flag_value
    for spec in [cls, *cls.__bases__]:
        flag_value = spec.__dict__.get(flag)
        if flag_value is not None:
            return flag_value
    raise FlagNotDefined(cls, flag)


cdef dict[object_id, cls_init_flags] _init_flags_cache = {}


cdef inline cls_init_flags _get_init_flags(PyTypeObject *cls_ptr):
    cdef cls_init_flags init_flags
    cdef object init_method = (<object>cls_ptr).__init__
    # We keep a smaller dict if we use the id of the method instead of the class
    cdef object_id init_method_id = id(init_method)
    init_flags = _init_flags_cache.get(init_method_id)
    if init_flags is None:
        init_flags = {k: v for k, v in signature(init_method).parameters.items() if k in VIABLE_FLAGS}
        _init_flags_cache[init_method_id] = init_flags
    return init_flags
