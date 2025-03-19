from asyncio import Lock, iscoroutinefunction
from collections import defaultdict
from functools import wraps
from typing import Any, DefaultDict, Dict

from a_sync._property import AwaitableProxy
from a_sync._property cimport AwaitableOnly
from a_sync._smart cimport shield
from a_sync.functools import update_wrapper


def async_cached_property(func, *args, **kwargs) -> "AsyncCachedPropertyDescriptor":
    assert iscoroutinefunction(func), "Can only use with async def"
    return AsyncCachedPropertyDescriptor(func, *args, **kwargs)


cdef class AsyncCachedPropertyInstanceState:
    def __cinit__(self) -> None:
        self.cache: Dict[FieldName, Any] = {}
        self.locks: DefaultDict[FieldName, Lock] = defaultdict(Lock)
    
    cdef object get_lock(self, str field_name):
        return self.locks[field_name]
    
    cdef object get_cache_value(self, str field_name):
        return self.cache[field_name]


class AsyncCachedPropertyDescriptor:
    _load_value = None

    def __init__(self, _fget, _fset=None, _fdel=None, field_name=None) -> None:
        self._fget = _fget
        self._fset = _fset
        self._fdel = _fdel
        self.field_name = field_name or _fget.__name__

        update_wrapper(self, _fget)
        self._check_method_sync(_fset, "setter")
        self._check_method_sync(_fdel, "deleter")

    def __set_name__(self, owner, name):
        self.field_name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        cache = (<AsyncCachedPropertyInstanceState>self.get_instance_state(instance)).cache
        if self.field_name in cache:
            return AwaitableProxy(cache[self.field_name])
        return AwaitableOnly(self.get_loader(instance))

    def __set__(self, instance, value):
        if self._fset is not None:
            self._fset(instance, value)
        self.set_cache_value(instance, value)

    def __delete__(self, instance):
        if self._fdel is not None:
            self._fdel(instance)
        self.del_cache_value(instance)

    def setter(self, method):
        self._check_method_name(method, "setter")
        return type(self)(self._fget, method, self._fdel, self.field_name)

    def deleter(self, method):
        self._check_method_name(method, "deleter")
        return type(self)(self._fget, self._fset, method, self.field_name)

    def _check_method_name(self, method, method_type):
        if method.__name__ != self.field_name:
            raise AssertionError(f"@{self.field_name}.{method_type} name must match property name")

    def _check_method_sync(self, method, method_type):
        if method and iscoroutinefunction(method):
            raise AssertionError(f"@{self.field_name}.{method_type} must be synchronous")

    def get_instance_state(self, instance):
        try:
            return instance.__async_property__
        except AttributeError:
            state = AsyncCachedPropertyInstanceState()
            instance.__async_property__ = state
            return state

    def get_lock(self, instance):
        return (<AsyncCachedPropertyInstanceState>self.get_instance_state(instance)).get_lock(self.field_name)

    def get_cache(self, instance):
        return (<AsyncCachedPropertyInstanceState>self.get_instance_state(instance)).cache

    def has_cache_value(self, instance):
        return self.field_name in (<AsyncCachedPropertyInstanceState>self.get_instance_state(instance)).cache

    def get_cache_value(self, instance):
        return (<AsyncCachedPropertyInstanceState>self.get_instance_state(instance)).get_cache_value(self.field_name)

    def set_cache_value(self, instance, value):
        (<AsyncCachedPropertyInstanceState>self.get_instance_state(instance)).cache[self.field_name] = value

    def del_cache_value(self, instance):
        del (<AsyncCachedPropertyInstanceState>self.get_instance_state(instance)).cache[self.field_name]

    def get_loader(self, instance):

        loader = self._load_value
        if loader is None:

            field_name = self.field_name
            _fget = self._fget
            get_lock = self.get_lock
            get_instance_state = self.get_instance_state
            set_cache_value = self.__set__

            @wraps(_fget)
            async def loader(instance):
                async with get_lock(instance):
                    cache = get_instance_state(instance).cache
                    if field_name in cache:
                        return cache[field_name]
                    value = await _fget(instance)
                    set_cache_value(instance, value)
                    return value

            self._load_value = loader

        return lambda: shield(loader(instance))
