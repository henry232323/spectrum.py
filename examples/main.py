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
        print("We're ready!")


myclient = MyClient(
    token=token,
    device_id=device_id
)


async def run():
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(myclient.run(), loop)
    await asyncio.Event().wait()


asyncio.run(run())
