import asyncio
import collections
import functools
import typing

from a_sync._smart cimport shield
from a_sync.async_property.proxy import AwaitableProxy
from a_sync.async_property.proxy cimport AwaitableOnly
from a_sync.functools cimport update_wrapper

# cdef asyncio
cdef object iscoroutinefunction = asyncio.iscoroutinefunction
cdef object Lock = asyncio.Lock
del asyncio

# cdef collections
cdef object defaultdict = collections.defaultdict
del collections

# cdef functools
cdef object wraps = functools.wraps
del functools

# cdef typing
cdef object Any = typing.Any
cdef object DefaultDict = typing.DefaultDict
cdef object Dict = typing.Dict
del typing


cdef object _AwaitableProxy = AwaitableProxy


def async_cached_property(func, *args, **kwargs) -> "AsyncCachedPropertyDescriptor":
    assert iscoroutinefunction(func), "Can only use with async def"
    return __AsyncCachedPropertyDescriptor(func, *args, **kwargs)


cdef class AsyncCachedPropertyInstanceState:
    def __cinit__(self) -> None:
        self.cache: Dict[FieldName, Any] = {}
        self.locks: DefaultDict[FieldName, Lock] = defaultdict(Lock)
    
    cdef object get_lock(self, str field_name):
        return self.locks[field_name]
    
    cdef object get_cache_value(self, str field_name):
        return self.cache[field_name]


cdef class _Loader:
    cdef readonly object func
    cdef readonly object instance
    def __cinit__(self, object func, object instance) -> None:
        self.func = func
        self.instance = instance
    def __call__(self):
        return shield(self.func(self.instance))


cdef class _AsyncCachedPropertyDescriptor:
    cdef readonly str field_name
    cdef readonly object _fget
    cdef readonly object _fset
    cdef readonly object _fdel
    cdef readonly object _load_value
    
    def __init__(self, _fget, _fset, _fdel, field_name) -> None:
        self._fget = _fget
        self.field_name = field_name or _fget.__name__
        
        self._check_method_sync(_fset, "setter")
        self._fset = _fset
        
        self._check_method_sync(_fdel, "deleter")
        self._fdel = _fdel

        # this will be set later
        self._load_value = None

    def setter(self, method):
        self._check_method_name(method, "setter")
        return type(self)(self._fget, method, self._fdel, self.field_name)

    def deleter(self, method):
        self._check_method_name(method, "deleter")
        return type(self)(self._fget, self._fset, method, self.field_name)

    cpdef AsyncCachedPropertyInstanceState get_instance_state(self, object instance):
        try:
            return instance.__async_property__
        except AttributeError:
            state = AsyncCachedPropertyInstanceState()
            instance.__async_property__ = state
            return state

    cpdef object get_lock(self, object instance):
        return self.get_instance_state(instance).get_lock(self.field_name)

    cpdef dict[str, object] get_cache(self, object instance):
        return self.get_instance_state(instance).cache

    cpdef bint has_cache_value(self, object instance):
        return self.field_name in self.get_instance_state(instance).cache

    cpdef object get_cache_value(self, object instance):
        return self.get_instance_state(instance).get_cache_value(self.field_name)

    cpdef void set_cache_value(self, instance, value):
        self.get_instance_state(instance).cache[self.field_name] = value

    cpdef void del_cache_value(self, instance):
        del self.get_instance_state(instance).cache[self.field_name]

    cpdef object get_loader(self, object instance):
        cdef object loader = self._load_value
        if loader is None:
            loader = self._load_value = self._make_loader(instance)
        return _Loader(loader, instance)

    cdef object _make_loader(self, object instance):
        cdef str field_name = self.field_name
        cdef object _fget = self._fget

        if self._fset is None:
            @wraps(_fget)
            async def loader(instance):
                cdef AsyncCachedPropertyInstanceState instance_state
                cdef dict[str, object] cache

                instance_state = self.get_instance_state(instance)
                locks: defaultdict = instance_state.locks
                async with locks[field_name]:
                    cache = instance_state.cache
                    if field_name in cache:
                        return cache[field_name]
                    value = await _fget(instance)
                    cache[field_name] = value
                    dict.pop(locks, field_name)
                    return value
                
        else:
            
            _fset = self._fset

            @wraps(_fget)
            async def loader(instance):
                cdef AsyncCachedPropertyInstanceState instance_state
                cdef dict[str, object] cache

                instance_state = self.get_instance_state(instance)
                cache = instance_state.cache
                locks: defaultdict = instance_state.locks
                async with locks[field_name]:
                    if field_name in cache:
                        return cache[field_name]
                    value = await _fget(instance)
                    _fset(instance, value)
                    cache[field_name] = value
                    dict.pop(locks, field_name)
                    return value
        
        return loader


    cdef void _check_method_name(self, object method, str method_type):
        if method.__name__ != self.field_name:
            raise AssertionError(f"@{self.field_name}.{method_type} name must match property name")

    cdef void _check_method_sync(self, object method, str method_type):
        if method and iscoroutinefunction(method):
            raise AssertionError(f"@{self.field_name}.{method_type} must be synchronous")

        
class AsyncCachedPropertyDescriptor(_AsyncCachedPropertyDescriptor):
    def __init__(self, _fget, _fset=None, _fdel=None, field_name=None) -> None:
        self._fget = _fget
        self._fset = _fset
        self._fdel = _fdel
        self.field_name = field_name or _fget.__name__
        self.__c_helper = _AsyncCachedPropertyDescriptor(_fget, _fset, _fdel, field_name)
        update_wrapper(self, _fget)
        self.setter = self.__c_helper.setter
        self.deleter = self.__c_helper.deleter
        self.get_instance_state = self.__c_helper.get_instance_state
        self.get_lock = self.__c_helper.get_lock
        self.get_cache = self.__c_helper.get_cache
        self.has_cache_value = self.__c_helper.has_cache_value
        self.get_cache_value = self.__c_helper.get_cache_value
        self.set_cache_value = self.__c_helper.set_cache_value
        self.del_cache_value = self.__c_helper.del_cache_value
        self.get_loader = self.__c_helper.get_loader

    def __set_name__(self, owner, name):
        self.field_name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        cdef dict cache = self.__c_helper.get_instance_state(instance).cache
        cdef str field_name = self.field_name
        if field_name in cache:
            return _AwaitableProxy(cache[field_name])
        return AwaitableOnly(self.get_loader(instance))

    def __set__(self, instance, value):
        if self._fset is not None:
            self._fset(instance, value)
        self.set_cache_value(instance, value)

    def __delete__(self, instance):
        if self._fdel is not None:
            self._fdel(instance)
        self.del_cache_value(instance)

cdef object __AsyncCachedPropertyDescriptor = AsyncCachedPropertyDescriptor
