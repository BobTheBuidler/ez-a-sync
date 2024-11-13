def work():
    """Simulates a time-consuming task by sleeping for 5 seconds."""
    import time

    time.sleep(5)


from a_sync import ProcessPoolExecutor


@pytest.mark.asyncio
async def test_executor():
    """Tests the ProcessPoolExecutor by running and submitting the work function asynchronously."""
    executor = ProcessPoolExecutor(6)
    await executor.run(work())
    await executor.submit(work())