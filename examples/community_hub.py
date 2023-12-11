import asyncio

from spectrum import CommunityHubClient


async def run():
    client = CommunityHubClient()
    print(await client.fetch_user_profile("Khuzdul"))


asyncio.run(run())
