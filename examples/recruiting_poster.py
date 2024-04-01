import asyncio
import logging
import os

from dotenv import load_dotenv

from spectrum import Client, Lobby

load_dotenv()
token = os.environ.get("RSI_TOKEN")
device_id = os.environ.get("DEVICE_ID")

logging.getLogger().setLevel(logging.DEBUG)

interval = 60 * 60  # seconds
lobby_id = 8  # Recruiting


class RecruitingBot(Client):
    lobby: Lobby = None
    running = False

    async def on_ready(self):
        self.lobby = self.get_lobby(lobby_id)
        asyncio.ensure_future(self.post_task())
        print("We're ready!")

    async def post_task(self):
        if self.running:
            return

        self.running = True
        try:
            while self.running:
                try:
                    await self.post_recruitment()
                except Exception as e:
                    logging.error("Error occurred while posting: %s", e)

                await asyncio.sleep(interval)
        finally:
            self.running = False

    async def post_recruitment(self):
        async for item in self.lobby.fetch_history(1):
            # Only send if the last message is not from @me
            if item.author != self.me:
                #await self.lobby.send('recruiting')
                print("WOWEE!")

            break


async def run():
    myclient = RecruitingBot(
        rsi_token=token,
        device_id=device_id
    )

    asyncio.ensure_future(myclient.run())
    await asyncio.Event().wait()


asyncio.run(run())
