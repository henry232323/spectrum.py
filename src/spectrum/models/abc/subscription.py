from .hasclient import HasClient


class Subscription(HasClient):
    subscription_key: str

    async def subscribe(self):
        await self._client.subscribe_to_topic(self.subscription_key)
