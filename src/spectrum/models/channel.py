from . import abc
from .. import httpclient


class Label(abc.Identifier, abc.Subscription):
    """
    {
        "id": "1",
        "channel_id": "1",
        "name": "Community",
        "subscription_key": "community:1:forum_label:1:ef02e5e178d66ec40e15e4e114974a91d31682dc",
        "notification_subscription": null
    },
    """

    def __init__(self, client, payload):
        self._client = client
        self.id = payload['id']
        self.channel_id = payload['channel_id']
        self.name = payload['name']
        self.subscription_key = payload['subscription_key']
        self.notification_subscription = payload['notification_subscription']

    @property
    def channel(self):
        return self._client.get_channel(self.channel_id)


class Channel(abc.Identifier, abc.Subscription):
    """
        {
            "0": {
                "id": "1",
                "community_id": "1",
                "group_id": "1",
                "order": 0,
                "name": "Announcements",
                "description": "Official Star Citizen announcements.",
                "color": "e05248",
                "sort_filter": "time-created",
                "label_required": false,
                "threads_count": 308,
                "labels": [
                    {
                        "id": "1",
                        "channel_id": "1",
                        "name": "Community",
                        "subscription_key": "community:1:forum_label:1:ef02e5e178d66ec40e15e4e114974a91d31682dc",
                        "notification_subscription": null
                    },
                    {
                        "id": "3",
                        "channel_id": "1",
                        "name": "Live Service",
                        "subscription_key": "community:1:forum_label:3:bd6ea6c5a7923607219bdb079b30babc985cfc98",
                        "notification_subscription": null
                    },
                    {
                        "id": "2",
                        "channel_id": "1",
                        "name": "Patch",
                        "subscription_key": "community:1:forum_label:2:45189c79a69c364c17db0dcc8228f4286835edc3",
                        "notification_subscription": null
                    },
                    {
                        "id": "5",
                        "channel_id": "1",
                        "name": "Spectrum",
                        "subscription_key": "community:1:forum_label:5:1e0a0aacd1c6129e8ecff627fa6e1bef3d75e958",
                        "notification_subscription": null
                    },
                    {
                        "id": "4",
                        "channel_id": "1",
                        "name": "Store Update",
                        "subscription_key": "community:1:forum_label:4:71f9e271f721ea69f49786ddd8d5f838fb193a29",
                        "notification_subscription": null
                    }
                ],
                "subscription_key": "community:1:forum_channel:1:cb0800f05bdb0f3976e20adbd2c12a145b4a83ce",
                "permissions": {
                    "4": {
                        "create_thread": 0,
                        "manage": 0
                    },
                    "5": {
                        "create_thread": 0,
                        "manage": 0
                    },
                    "6": {
                        "create_thread": 0,
                        "manage": 0
                    },
                    "11": {
                        "create_thread": 0
                    },
                    "137732": {
                        "create_thread": 0,
                        "manage": 0
                    }
                },
                "notification_subscription": null
            }
        }
    """

    def __init__(self, client: 'httpclient.HTTPClient', payload):
        self._client = client
        self.id = int(payload["id"])
        self.community_id = int(payload["community_id"])
        self.group_id = int(payload["group_id"])
        self.order = payload["order"]
        self.name = payload["name"]
        self.description = payload["description"]
        self.color = payload["color"]
        self.sort_filter = payload["sort_filter"]
        self.label_required = payload["label_required"]
        self.subscription_key = payload["subscription_key"]
        self.threads_count = payload.get("threads_count", 0)
        self.labels = [Label(client, label) for label in payload.get("labels", [])]

        if payload.get("threads"):
            self._threads = {thread['id']: client._replace_thread(thread) for thread in payload['threads']}

    @property
    def threads(self):
        return list(self._client._threads.values())

    @property
    def community(self):
        return self._client.get_community(self.community_id)

    @property
    def forum(self):
        return self._client.get_forum(self.group_id)

    async def create_thread(
            self,
            subject: str,
            plaintext: str,
            type="discussion",
            label_id=None,
            content_blocks=None,
            highlight_role_id=None,
            is_locked=False,
            is_reply_nesting_disabled=False
    ):
        resp = await self._client._http.create_thread(
            {
                "type": type,
                "channel_id": self.id,
                "label_id": label_id,
                "subject": subject,
                "content_blocks": content_blocks or [
                    {
                        "id": 1,
                        "type": "text",
                        "data": {
                            "blocks": [
                                {
                                    "key": "dr2qu",
                                    "text": plaintext,
                                    "type": "unstyled",
                                    "depth": 0,
                                    "inlineStyleRanges": [],
                                    "entityRanges": [],
                                    "data": {}
                                }
                            ],
                            "entityMap": {}
                        }
                    }
                ],
                "plaintext": plaintext,
                "highlight_role_id": highlight_role_id,
                "is_locked": is_locked,
                "is_reply_nesting_disabled": is_reply_nesting_disabled
            }
        )

        thread = self._client._replace_thread(resp)
        self.threads[thread.id] = thread
        return thread

    async def fetch_threads(self, max_count=None, label_id=None):
        resp = await self._client._http.fetch_threads(
            {"channel_id": self.id, "page": 1, "sort": "hot", "label_id": label_id})
        threads_count = resp['threads_count']
        thread_data = resp['threads']
        threads = []
        if max_count and len(threads) >= max_count:
            for item in thread_data:
                thread = self._client._replace_thread(item)
                self.threads[item['id']] = thread

            return threads

        page = 2

        while len(threads) <= threads_count:
            resp = await self._client._http.fetch_threads(
                {"channel_id": self.id, "page": page, "sort": "hot", "label_id": label_id})
            thread_data = resp['threads']
            for item in thread_data:
                thread = self._client._replace_thread(item)
                self.threads[item['id']] = thread

            page += 1
            if max_count and len(threads) >= max_count:
                return threads

        self.threads.clear()
        for thread in threads:
            self.threads[thread.id] = thread
