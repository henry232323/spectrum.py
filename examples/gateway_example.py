import asyncio
import os

from dotenv import load_dotenv

from spectrum import Client, Message

load_dotenv()
token = os.environ.get("RSI_TOKEN")
device_id = os.environ.get("DEVICE_ID")


class MyClient(Client):
    async def on_message(self, message: Message):
        print(message)

    async def on_ready(self):
        await self.subscribe_to_default()
        print("We're ready!")


async def run():
    myclient = MyClient(
        rsi_token=token,
        device_id=device_id
    )

    asyncio.create_task(myclient.run())
    await asyncio.Event().wait()


asyncio.run(run())
