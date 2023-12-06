import asyncio
import os

from dotenv import load_dotenv

from spectrum import HTTPClient

load_dotenv()
token = os.environ.get("RSI_TOKEN")
device_id = os.environ.get("DEVICE_ID")


async def run():
    client = HTTPClient(
        rsi_token=token,
        device_id=device_id
    )

    await client.identify()
    member = await client.fetch_member_by_handle("Khuzdul")
    print(member)

    await client.close()


asyncio.run(run())
