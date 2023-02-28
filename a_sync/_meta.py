
import threading
from abc import ABCMeta
from asyncio import iscoroutinefunction
from typing import Any, Dict, Tuple

from a_sync import _bound
from a_sync.property import (AsyncCachedPropertyDescriptor,
                             AsyncPropertyDescriptor)


class ASyncMeta(ABCMeta):
    """Any class with metaclass ASyncMeta will have its functions wrapped with a_sync upon class instantiation."""
    def __new__(cls, name, bases, attrs):
        
        # Wrap all methods with a_sync abilities
        for attr_name, attr_value in list(attrs.items()):
            
            # Read modifiers from class definition
            fn_modifiers = cls.__a_sync_modifiers__ if hasattr(cls, '__a_sync_modifiers__') else {}
        
            # Special handling for functions decorated with async_property and async_cached_property
            if isinstance(attr_value, (AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor)):
                # Check for modifier overrides defined at the property decorator
                fn_modifiers.update(attr_value.modifiers)
                # Wrap property
                attrs[attr_name], attrs[attr_value.hidden_method_name] = _bound._wrap_property(attr_value, **fn_modifiers)
            elif iscoroutinefunction(attr_value):
                # NOTE We will need to improve this logic if somebody needs to use it with classmethods or staticmethods.
                # TODO: update modifiers with override decorators (or maybe the main deco?)
                # modifiers.update(overrides)
                # Wrap bound method
                attrs[attr_name] = _bound._wrap_bound_method(attr_value, **fn_modifiers)
        return super(ASyncMeta, cls).__new__(cls, name, bases, attrs)    


class ASyncSingletonMeta(ASyncMeta):
    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]) -> None:
        cls.__instances: Dict[bool, object] = {}
        cls.__lock = threading.Lock()
        super().__init__(name, bases, namespace)

    def __call__(cls, *args: Any, **kwargs: Any):
        is_sync = cls.__a_sync_instance_will_be_sync__(kwargs)  # type: ignore [attr-defined]
        if is_sync not in cls.__instances:
            with cls.__lock:
                # Check again in case `__instance` was set while we were waiting for the lock.
                if is_sync not in cls.__instances:
                    cls.__instances[is_sync] = super().__call__(*args, **kwargs)
        return cls.__instances[is_sync]
