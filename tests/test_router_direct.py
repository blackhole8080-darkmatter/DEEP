import asyncio
from interface.routers.etis import sandbox_execute

async def run():
    payload = {
        "code": "print(1)",
        "language": "python",
        "timeout": 30
    }
    result = await sandbox_execute(payload)
    print("Router returned:", result)

if __name__ == "__main__":
    asyncio.run(run())
