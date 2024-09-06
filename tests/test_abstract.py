
import pytest

from a_sync.a_sync.abstract import ASyncABC

def test_abc_direct_init():
    with pytest.raises(TypeError, match="Can't instantiate abstract class ASyncABC with abstract methods __a_sync_default_mode__, __a_sync_flag_name__, __a_sync_flag_value__"):
        ASyncABC()