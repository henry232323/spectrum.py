# spectrum.py

spectrum.py is a [discord.py](https://github.com/Rapptz/discord.py) style proof-of-concept library for making chatbots
for Star Citizen's [Spectrum](https://robertsspaceindustries.com/spectrum/community/SC) chat client.

## Installation
```shell
python -m pip install git+https://github.com/henry232323/spectrum.py
```

## Example
This example requires `python-dotenv`.
```python
import asyncio
import os
from dotenv import load_dotenv
from spectrum import Client, Message

load_dotenv()

class MyClient(Client):
    async def on_message(self, message: Message):
        print(message)

    async def on_ready(self):
        print("We're ready!")


async def run():
    myclient = MyClient(
        token=os.environ.get("RSI_TOKEN"),
        device_id=os.environ.get("DEVICE_ID")
    )

    asyncio.create_task(myclient.run())
    await asyncio.Event().wait()


asyncio.run(run())
```

## Authentication
The bot can be run in a read only state without any authentication. 
If you want to be able to send messages or read private messages (and eventually do other things),
you'll need to provide credentials for an RSI account. These can be found in the cookies sent
with any request to [RSI](https://robertsspaceindustries.com/) when logged in.

## Todo
- Fetch MOTD
- Fetch emojis

