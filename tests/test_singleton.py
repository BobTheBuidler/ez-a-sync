
from a_sync.singleton import ASyncGenericSingleton

def test_flag_predefined():
    """We had a failure case where the subclass implementation assigned the flag value to the class and did not allow user to determine at init time"""
    class Test(ASyncGenericSingleton):
        sync=True
        def __init__(self):
            ...
    Test()
    class TestInherit(Test):
        ...
    TestInherit()

    class Test(ASyncGenericSingleton):
        sync=False
    Test()
    class TestInherit(Test):
        ...
    TestInherit()