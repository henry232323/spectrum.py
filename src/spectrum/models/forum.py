from . import abc
from .. import httpclient


class Forum(abc.Identifier):
    """
    {
        "0": {
            "id": "1",
            "community_id": "1",
            "order": 0,
            "name": "Official",
            "channels": [ ... ]
        }
    }
    """

    def __init__(self, client: 'httpclient.HTTPClient', payload):
        self._client = client
        self.id = int(payload["id"])
        self.community_id = int(payload["community_id"])
        self.order = payload["order"]
        self.name = payload["name"]
        self.channels = tuple(client._replace_channel(channel) for channel in payload['channels'])

    @property
    def community(self):
        return self._client.get_community(self.community_id)

    async def create_channel(self, name: str, description: str, color: str, sort_filter=None,
                             label_required: bool = False):
        resp = await self._client._http.create_category(
            {"community_id": self.community_id, "group_id": self.id, "name": name, "description": description,
             "color": color, "sort_filter": sort_filter, "label_required": label_required}
        )

        channel = self._client._replace_channel(resp)
        self.channels = (*self.channels, channel)
        return channel
