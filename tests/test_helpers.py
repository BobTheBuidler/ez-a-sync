import asyncio

from a_sync.asyncio import get_event_loop


def test_get_event_loop():
    assert get_event_loop() == asyncio.get_event_loop()


def test_get_event_loop_in_thread():
    def task():
        assert get_event_loop() == asyncio.get_event_loop()

    loop = get_event_loop()
    loop.run_until_complete(loop.run_in_executor(None, task))
