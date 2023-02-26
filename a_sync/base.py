
from a_sync import _helpers
from a_sync._meta import ASyncMeta

class ASyncBase(metaclass=ASyncMeta):
    """Inherit from this class to a-syncify all of your bound methods."""
    pass

    def _should_await(self, kwargs: dict) -> bool:
        """Returns a boolean that indicates whether methods of 'instance' should be called as sync or async methods."""
        flags = _helpers._flag_name_options

        # Defer to kwargs always
        if any(flag in kwargs for flag in flags):
            for flag in flags:
                if flag in kwargs:
                    sync = kwargs[flag]
                    assert isinstance(sync, bool), f"{flag} must be boolean. You passed {sync}."
                    if flag == 'asynchronous':
                        # must invert
                        return not sync
                    return sync
        
        # No flag found in kwargs, check for a flag attribute.
        for flag in flags:
            if hasattr(self, flag):
                sync = getattr(self, flag)
                assert isinstance(sync, bool), f"{flag} must be boolean. You passed {sync}."
                if flag == 'asynchronous':
                    # must invert
                    return not sync
                return sync
        raise RuntimeError(f"{self} must have one of the following properties to tell a_sync how to proceed: {_helpers._flag_name_options}")