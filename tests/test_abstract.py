
import sys

import pytest

from a_sync.a_sync.abstract import ASyncABC

if sys.version_info >= (3, 12):
    _MIDDLE = "without an implementation for"
else:
    _MIDDLE = "with abstract methods"

def test_abc_direct_init():
    with pytest.raises(TypeError, match=f"Can't instantiate abstract class ASyncABC {_MIDDLE} __a_sync_default_mode__, __a_sync_flag_name__, __a_sync_flag_value__"):
        ASyncABC()