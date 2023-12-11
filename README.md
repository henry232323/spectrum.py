# spectrum.py

spectrum.py is a [discord.py](https://github.com/Rapptz/discord.py) style proof-of-concept library for making chatbots
for Star Citizen's [Spectrum](https://robertsspaceindustries.com/spectrum/community/SC) chat client. It also offers HTTP clients for interacting
with both Spectrum's REST API and the Community Hub's GraphQL API.

## Installation
```shell
# Latest Release
python -m pip install spectrum.py
# Latest in Github
python -m pip install git+https://github.com/henry232323/spectrum.py
```

## Examples
### With Gateway
```python
import asyncio
from spectrum import Client, Message

class MyClient(Client):
    async def on_message(self, message: Message):
        print(message)

    async def on_ready(self):
        print("We're ready!")


async def run():
    myclient = MyClient(
        rsi_token=...,
        device_id=...,
    )

    asyncio.create_task(myclient.run())
    await asyncio.Event().wait()


asyncio.run(run())
```

### HTTP Only

```python
import asyncio
from spectrum import HTTPClient

async def run():
    client = HTTPClient(
        rsi_token=...,
        device_id=...,
    )

    await client.identify()
    member = await client.fetch_member_by_handle("Khuzdul")
    print(member)

    await client.close()

asyncio.run(run())
```

### Community Hub
```python
import asyncio
from spectrum import CommunityHubClient

async def run():
    client = CommunityHubClient()
    print(await client.fetch_user_profile("Khuzdul"))

asyncio.run(run())
```

## Authentication
The bot can be run in a read only state without any authentication. 
If you want to be able to send messages or read private messages (and eventually do other things),
you'll need to provide credentials for an RSI account. These can be found in the cookies sent
with any request to [RSI](https://robertsspaceindustries.com/) when logged in.

