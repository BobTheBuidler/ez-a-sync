
from asyncio import iscoroutinefunction

from a_sync import _bound, _descriptors

class ASyncMeta(type):
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
