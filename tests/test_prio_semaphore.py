import pytest

from a_sync import PrioritySemaphore


def test_prio_semaphore_init():
    assert PrioritySemaphore(1)._value == 1
    with_name = PrioritySemaphore(10, name="test")
    assert with_name._value == 10 and with_name.name == "test"


@pytest.mark.asyncio
async def test_prio_semaphore_use():
    semaphore = PrioritySemaphore(1)
    assert semaphore._value == 1
    # await semaphore.acquire()
    # assert semaphore._value == 0
    # semaphore.release()
    assert semaphore._value == 1
    print("entering")

    cm = semaphore[100]
    # print(cm)
    async with cm:
        print("entered")
        assert semaphore._value == 0
        print("exiting")
    print("exited")
    assert semaphore._value == 1
    async with semaphore:
        assert semaphore._value == 0
    assert semaphore._value == 1