from a_sync.a_sync.singleton import ASyncGenericSingleton


def test_flag_predefined():
    """Test predefined sync flag in ASyncGenericSingleton subclasses.

    This test verifies that the `sync` flag can be predefined in a subclass of
    `ASyncGenericSingleton` and that it allows the user to determine the sync/async
    mode at initialization time. It checks if the `sync` attribute can be set to
    `True` or `False` in subclasses and whether instances can be created without errors.

    The test ensures that the `sync` flag is correctly interpreted and does not
    interfere with the instantiation of subclasses.

    See Also:
        - :class:`a_sync.a_sync.singleton.ASyncGenericSingleton` for more details on the base class.
    """

    class Test(ASyncGenericSingleton):
        sync = True

        def __init__(self): ...

    Test()

    class TestInherit(Test): ...

    TestInherit()

    class Test(ASyncGenericSingleton):
        sync = False

    Test()

    class TestInherit(Test): ...

    TestInherit()
