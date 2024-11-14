import sys

import pytest

from a_sync.a_sync.abstract import ASyncABC

_methods = "__a_sync_default_mode__", "__a_sync_flag_name__", "__a_sync_flag_value__"
if sys.version_info >= (3, 12):
    _MIDDLE = "without an implementation for abstract methods"
    _methods = (f"'{method}'" for method in _methods)
else:
    _MIDDLE = "with abstract methods"


def test_abc_direct_init():
    """Test that ASyncABC cannot be instantiated directly.

    This test verifies that attempting to instantiate the abstract base class
    `ASyncABC` raises a `TypeError`. This is expected behavior for abstract
    base classes in Python, which require subclasses to implement all abstract
    methods before instantiation.

    Raises:
        TypeError: If `ASyncABC` is instantiated without implementing abstract methods.

    Example:
        >>> from a_sync.a_sync.abstract import ASyncABC
        >>> ASyncABC()
        TypeError: Can't instantiate abstract class ASyncABC with abstract methods ...
    """
    with pytest.raises(
        TypeError,
        match=f"Can't instantiate abstract class ASyncABC {_MIDDLE} {', '.join(_methods)}",
    ):
        ASyncABC()
