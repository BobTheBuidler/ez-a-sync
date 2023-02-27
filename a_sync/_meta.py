
import threading
from abc import ABCMeta
from asyncio import iscoroutinefunction
from typing import Any, Dict, Tuple

from a_sync import _bound, _descriptors


class ASyncMeta(ABCMeta):
    """Any class with metaclass ASyncMeta will have its functions wrapped with a_sync upon class instantiation."""
    def __new__(cls, name, bases, attrs):
        for attr_name, attr_value in list(attrs.items()):
            # Special handling for functions decorated with async_property and async_cached_property
            if isinstance(attr_value, (_descriptors.AsyncPropertyDescriptor, _descriptors.AsyncCachedPropertyDescriptor)):
                attrs[attr_name], attrs[attr_value.hidden_method_name] = _bound.a_sync_property(attr_value)
            elif iscoroutinefunction(attr_value):
                # NOTE We will need to improve this logic if somebody needs to use it with classmethods or staticmethods.
                attrs[attr_name] = _bound.a_sync(attr_value)
        return super(ASyncMeta, cls).__new__(cls, name, bases, attrs)


class ASyncSingletonMeta(ASyncMeta):
    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]) -> None:
        cls.__instances = {}
        cls.__lock = threading.Lock()
        super().__init__(name, bases, namespace)

    def __call__(cls, *args: Any, **kwargs: Any):
        is_sync = cls.__a_sync_instance_will_be_sync__(kwargs)
        if is_sync not in cls.__instances:
            with cls.__lock:
                # Check again in case `__instance` was set while we were waiting for the lock.
                if is_sync not in cls.__instances:
                    cls.__instances[is_sync] = super().__call__(*args, **kwargs)
        return cls.__instances[is_sync]
