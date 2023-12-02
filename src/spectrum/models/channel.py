from . import abc


class Channel(abc.Identifier):
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

    def __init__(self, client, payload):
        self._client = client
        self.id = payload["id"]
        self.community_id = payload["community_id"]
        self.group_id = payload["group_id"]
        self.order = payload["order"]
        self.name = payload["name"]
        self.description = payload["description"]
        self.color = payload["color"]
        self.sort_filter = payload["sort_filter"]
        self.label_required = payload["label_required"]
        self.threads_count = payload["threads_count"]
        self.labels = payload["labels"]

    @property
    def community(self):
        return self._client.get_community(self.community_id)

    @property
    def forum(self):
        return self._client.get_forum(self.group_id)