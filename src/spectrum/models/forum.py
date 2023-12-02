from . import abc


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

    def __init__(self, client, payload):
        self._client = client
        self.id = payload["id"]
        self.community_id = payload["community_id"]
        self.order = payload["order"]
        self.name = payload["name"]
        self.channels = tuple(client._replace_channel(channel) for channel in payload['channels'])

    @property
    def community(self):
        return self._client.get_community(self.community_id)
