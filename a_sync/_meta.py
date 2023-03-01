
import threading
from abc import ABCMeta
from typing import Any, Dict, Tuple

from a_sync import _bound, modifiers
from a_sync.modified import ASyncFunction, Modified
from a_sync.property import PropertyDescriptor


class ASyncMeta(ABCMeta):
    """Any class with metaclass ASyncMeta will have its functions wrapped with a_sync upon class instantiation."""
    def __new__(cls, name, bases, attrs):
        # Wrap all methods with a_sync abilities
        for attr_name, attr_value in list(attrs.items()):
            # Read modifiers from class definition 
            # NOTE: Open uesion: what do we do when a parent class and subclass define the same modifier differently?
            #       Currently the parent value is used for functions defined on the parent, 
            #       and the subclass value is used for functions defined on the subclass.
            fn_modifiers = modifiers.get_modifiers_from(attrs)
            # Special handling for functions decorated with a_sync decorators
            if isinstance(attr_value, Modified):
                # Check for modifier overrides defined on the Modified object
                fn_modifiers.update(attr_value.modifiers._modifiers)
                if isinstance(attr_value, PropertyDescriptor):
                    # Wrap property
                    attrs[attr_name], attrs[attr_value.hidden_method_name] = _bound._wrap_property(attr_value, **fn_modifiers)
                elif isinstance(attr_value, ASyncFunction):
                    attrs[attr_name] = _bound._wrap_bound_method(attr_value, **fn_modifiers)
                else:
                    raise NotImplementedError(attr_name, attr_value)
                    
            if callable(attr_value) and "__" not in attr_name and not attr_name.startswith("_"):
                # NOTE We will need to improve this logic if somebody needs to use it with classmethods or staticmethods.
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
