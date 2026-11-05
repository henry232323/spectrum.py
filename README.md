# spectrum.py

spectrum.py is an unofficial, [discord.py](https://github.com/Rapptz/discord.py)-style async Python client for
[RSI Spectrum](https://robertsspaceindustries.com/spectrum/community/SC), the Star Citizen community platform.
Look up members and communities, read lobbies, forums and threads, and receive live events over the websocket.
It also includes small clients for other public RSI data (Starmap, Roadmap, Galactapedia, Orgs).

> **Unofficial.** spectrum.py is a community project. It is not made, endorsed or supported by Cloud Imperium Games
> or Roberts Space Industries. Star Citizen®, Roberts Space Industries® and Spectrum are trademarks of
> Cloud Imperium Rights LLC.
>
> **Be a good citizen.** This library talks to the same endpoints the Spectrum website uses. Those endpoints are
> undocumented and can change at any time. Don't post automated or repetitive messages in public lobbies, and
> follow each community's rules.
>
> **Your account, your responsibility.** Using an RSI session with any third-party software is subject to the
> [RSI Terms of Service](https://robertsspaceindustries.com/en/tos) and the Spectrum Code of Conduct. Read them
> before you sign in. Anonymous, read-only use needs no account. If you use a session, treat the token like a
> password and never commit it.

## Installation
```shell
# Latest Release
python -m pip install spectrum.py
# With the Community Hub / Store GraphQL clients
python -m pip install "spectrum.py[community-hub]"
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

    asyncio.ensure_future(myclient.run())
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

## User-Agent
Requests identify themselves as `spectrum.py/<version> (+https://github.com/henry232323/spectrum.py)`.
Pass `user_agent=` to `HTTPClient` or `Client` to change it:

```python
client = HTTPClient(user_agent="my-tool/1.0 (+https://example.com)")
```

## Transports
`Client` uses the Spectrum websocket by default. `Client(transport="grpc")` selects an **experimental** ConnectRPC
transport: it emits an `ExperimentalTransportWarning`, its protocol is partly inferred, and it may break or change
in any release. Don't rely on it.


## Spec and tests
`spec/` holds a machine-readable description of the Spectrum HTTP API (OpenAPI 3.1), the websocket events
(AsyncAPI 3.0), shared JSON Schemas and redacted fixtures. See [`spec/README.md`](spec/README.md).
Run the tests with:

```shell
python -m pip install -e ".[dev]"
python -m pytest
```
