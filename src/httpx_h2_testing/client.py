import asyncio

from httpx import AsyncClient


async def request(client: AsyncClient, port: int):
    await client.post(f"https://127.0.0.1:{port}", json={"test": True})


async def run_client(port: int, requests: int, warm: bool):
    async with AsyncClient(timeout=30, verify=False, http2=True) as client:
        todo = []
        if warm:
            await request(client, port)
        for _ in range(requests):
            todo.append(asyncio.create_task(request(client, port)))
            await asyncio.sleep(0)
        await asyncio.gather(*todo)
