import asyncio
import logging
import os

from dotenv import load_dotenv

from spectrum import Client, Message

load_dotenv()
token = os.environ.get("RSI_TOKEN")
device_id = os.environ.get("DEVICE_ID")

logging.getLogger().setLevel(logging.DEBUG)


class MyClient(Client):
    async def on_message(self, message: Message):
        print(message)

    async def on_ready(self):
        await self.subscribe_to_all()
        print("We're ready!")

    async def on_forum_thread_reply(self, reply):
        print(reply)

    async def on_forum_thread_new(self, thread):
        print(thread)
        # await self.subscribe_to_topic(thread.subscription_key)


async def run():
    myclient = MyClient(
        rsi_token=token,
        device_id=device_id
    )

    asyncio.ensure_future(myclient.run())
    await asyncio.Event().wait()


asyncio.run(run())
