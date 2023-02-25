
from a_sync import _helpers
from a_sync._meta import ASyncMeta

class ASyncBase(metaclass=ASyncMeta):
    """Inherit from this class to a-syncify all of your bound methods."""
    pass

    def _should_await(self, kwargs: dict) -> bool:
        """Returns a boolean that indicates whether methods of 'instance' should be called as sync or async methods."""
        for flag in _helpers._flag_name_options:
            try:
                sync = kwargs[flag] if flag in kwargs else getattr(self, flag)
            except AttributeError:
                continue
            assert isinstance(sync, bool), f"{flag} must be boolean. You passed {sync}."
            if flag == 'asynchronous':
                # must invert
                return not sync
            return sync
        raise RuntimeError(f"{self} must have one of the following properties to tell a_sync how to proceed: {_helpers._flag_name_options}")