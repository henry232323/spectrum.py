import asyncio
import os

from dotenv import load_dotenv

from spectrum import HTTPClient

load_dotenv()
token = os.environ.get("RSI_TOKEN")
device_id = os.environ.get("DEVICE_ID")


async def run():
    async with HTTPClient(rsi_token=token, device_id=device_id) as client:
        await client.identify()

        # Fetch a member by handle
        member = await client.fetch_member_by_handle("Khuzdul")
        print(member)

        # Search content
        results = await client.search_content(text="hello", sort="latest", range="week")
        print(f"Found {len(results)} results")

        # Fetch community members (requires admin permissions)
        for community in client.communities:
            result = await community.fetch_members()
            print(f"{community.name}: {result.total} members ({result.pages_total} pages)")


asyncio.run(run())
