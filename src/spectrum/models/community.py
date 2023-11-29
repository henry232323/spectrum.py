from .. import client


class Community:
    """
{
  "0": {
    "id": "1",
    "type": "public",
    "slug": "SC",
    "name": "Star Citizen",
    "avatar": "https://robertsspaceindustries.com/media/swz5gohfczhjqr/heap_infobox/SC_Gold.jpg?v=1503107521",
    "banner": "https://robertsspaceindustries.com/media/yos4xd23ikf96r/source/After_GC2017_SPECTRUMBANNER.jpg?v=1504636757",
    "lobbies": [
        Lobby
    ],
    "forum_channel_groups": {
      "0": {
        "id": "1",
        "community_id": "1",
        "order": 0,
        "name": "Official",
        "channels": [
          {
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
        ]
      },
    },
    "roles": [
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
    ]
  }
}
    """

    def __init__(self, client: 'client.Client', payload: dict):
        self._client = client
        self.id = payload['id']
        self.slug = payload['slug']
        self.name = payload['name']
        self.avatar_url = payload['avatar']
        self.banner_url = payload['banner']
        self.lobbies = tuple(client._replace_lobby(lobby) for lobby in payload['lobbies'])

    def __repr__(self):
        return f"Community(id={repr(self.id)}, name={repr(self.name)}, slug={repr(self.slug)})"