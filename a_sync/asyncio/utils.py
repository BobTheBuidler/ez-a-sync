import asyncio


def get_event_loop() -> asyncio.AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError as e:  # Necessary for use with multi-threaded applications.
        if not str(e).startswith("There is no current event loop in thread"):
            raise
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop
