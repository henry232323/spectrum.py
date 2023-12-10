import asyncio
import os

import discord
from dotenv import load_dotenv

import spectrum

load_dotenv()
discord_token = os.environ.get("DISCORD_TOKEN")
discord_channel_id = os.environ.get("DISCORD_CHANNEL_ID")
rsi_token = os.environ.get("RSI_TOKEN")
device_id = os.environ.get("DEVICE_ID")
rsi_lobby_id = os.environ.get("RSI_LOBBY_ID")


class DiscordClient(discord.Client):
    channel = None
    webhook = None

    async def on_message(self, message: discord.Message):
        if message.author.id == self.user.id:
            return

        if message.channel == self.channel:
            await spectrum_client.lobby.send(f"[{message.author.name}] {message.content}")

    async def on_ready(self):
        self.channel = self.get_channel(int(discord_channel_id))
        webhooks = await self.channel.webhooks()
        for webhook in webhooks:
            if webhook.name == "SpectrumBridge":
                self.webhook = webhook
                break
        else:
            self.webhook = await self.channel.create_webhook(name="SpectrumBridge")


class SpectrumClient(spectrum.Client):
    lobby = None

    async def on_message(self, message: spectrum.Message):
        if message.author.id == self.me.id:
            return

        if message.lobby.id == self.lobby.id:
            await discord_client.webhook.send(
                content=message.plaintext,
                username=message.author.displayname,
                avatar_url=message.author.avatar_url,
            )

    async def on_ready(self):
        self.lobby = self.get_lobby(rsi_lobby_id)
        await self.subscribe_to_topic(self.lobby.subscription_key)
        print("We're ready!")


spectrum_client: SpectrumClient
discord_client: DiscordClient


async def run():
    global spectrum_client, discord_client

    spectrum_client = SpectrumClient(
        rsi_token=rsi_token,
        device_id=device_id
    )

    intents = discord.Intents.default()
    intents.members = True
    intents.reactions = True
    intents.message_content = True

    discord_client = DiscordClient(
        intents=intents,
    )

    asyncio.create_task(spectrum_client.run())
    asyncio.create_task(discord_client.start(token=discord_token))

    await asyncio.Event().wait()


asyncio.run(run())
