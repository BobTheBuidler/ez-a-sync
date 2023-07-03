def work():
    import time
    time.sleep(5)

from a_sync import ProcessPoolExecutor

@pytest.marks.asyncio
async def test_executor():
    executor = ProcessPoolExecutor(6)
    await executor.run(work())
    await executor.submit(work())
