from . import abc
from .permissions import Permissions
from .. import httpclient


class Role(abc.Identifier):
    """
    {
        "id": "1",
        "community_id": "1",
        "type": "admin",
        "order": 0,
        "visible": false,
        "highlightable": true,
        "tracked": false,
        "name": "admin",
        "description": "Spectrum Administrator",
        "color": "FF6262",
        "member_count": null,
        "members_count": null,
        "permissions": {
          "global": {
            "manage_roles": true,
            "kick_members": true,
            "embed_link": true,
            "upload_media": true,
            "mention": true,
            "reaction": true,
            "vote": true,
            "read_erased": true
          },
          "message_lobby": {
            "read": true,
            "send_message": true,
            "manage": true,
            "moderate": true,
            "set_motd": true
          },
          "forum_channel": {
            "read": true,
            "create_thread": true,
            "create_thread_reply": true,
            "manage": true,
            "moderate": true
          },
          "custom_emoji": {
            "create": true,
            "remove": true
          }
        }
    },
    """

    def __init__(self, client: 'httpclient.HTTPClient', payload: dict):
        self._client = client
        self.id = int(payload["id"])
        self.community_id = int(payload["community_id"])
        self.type = payload["type"]
        self.order = payload["order"]
        self.visible = payload["visible"]
        self.highlightable = payload["highlightable"]
        self.tracked = payload["tracked"]
        self.name = payload["name"]
        self.description = payload["description"]
        self.color = payload["color"]
        self.member_count = payload["member_count"]
        self.members_count = payload["members_count"]
        self.permissions = Permissions.from_payload(payload["permissions"])

    @property
    def community(self):
        return self._client.get_community(self.community_id)

    def __repr__(self):
        return f"Role(id={repr(self.id)}, name={repr(self.name)})"
