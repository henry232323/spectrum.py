class Presence:
    """{"status": "playing", "info": "Playing Star Citizen", "since": 1701335977}"""
    def __init__(self, client, payload):
        self._client = client
        self.status = payload["status"]
        self.info = payload["info"]
        self.since = payload.get("since")