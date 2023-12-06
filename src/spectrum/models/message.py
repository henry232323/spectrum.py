from datetime import datetime
from typing import Optional

from . import lobby, abc, member
from .content import ContentState, Media
from .. import httpclient


class Message(abc.Identifier):
    """
    ```json
    {
      type: "message.new",
      message: {
        id: "50828997",
        time_created: 1701262865,
        time_modified: 1701262865,
        member_id: "4136837",
        is_erased: null,
        erased_by: null,
        lobby_id: "1",
        media_id: null,
        content_state: {
          blocks: [
            {
              key: "bnt0p",
              text: "so when they can kill you and steal your ship in the future will you be calling for the end to ship sales?",
              type: "unstyled",
              depth: 0,
              inlineStyleRanges: [],
              entityRanges: [],
              data: [],
            },
          ],
          entityMap: [],
        },
        plaintext:
          "so when they can kill you and steal your ship in the future will you be calling for the end to ship sales?",
        highlight_role_id: "",
        member: {
          id: "4136837",
          displayname: "Badwolfe",
          nickname: "Badwolfe",
          avatar:
            "https://robertsspaceindustries.com/media/rbj826kojz454r/heap_infobox/Wolf-Logo-Trans.png?v=1700823940",
          signature: "",
          meta: {
            badges: [
              {
                name: "High Admiral",
                icon: "https://media.robertsspaceindustries.com/i5zz45wyvg30r/heap_note.png",
              },
              {
                name: "PACK",
                icon: "https://cdn.robertsspaceindustries.com/static/images/organization/defaults/thumbnail/generic.png",
                url: "https://robertsspaceindustries.com/orgs/PCK",
              },
            ],
          },
          isGM: false,
          spoken_languages: [],
        },
        "media":{
             "id":"embed:v9q0cduqji9ts",
             "slug":"v9q0cduqji9ts",
             "type":"embed",
             "data":{
                "embed_type":"photo",
                "url":"https://i.imgur.com/CZhdJhI.jpg",
                "provider_name":"imgur",
                "title":"https://i.imgur.com/CZhdJhI.jpg",
                "description":"None",
                "image":"https://i.imgur.com/CZhdJhI.jpg",
                "image_width":2389,
                "image_height":1194,
                "provider_icon":"https://robertsspaceindustries.com/imager/03DdxgGU7GTCdfcPLRGx6G-JqUw=/https://imgur.com/favicon.ico",
                "time_fetched":1701574988,
                "sizes":{
                   "mini":{
                      "url":"https://robertsspaceindustries.com/imager/dR5-BtQ6b-k2L2fy4axXjn1c_Ag=/150x100/https://i.imgur.com/CZhdJhI.jpg",
                      "image_width":150,
                      "image_height":150
                   },
                   "square":{
                      "url":"https://robertsspaceindustries.com/imager/keOLWxOLRCtc92Ao0LCHzHcgF0E=/250x250/https://i.imgur.com/CZhdJhI.jpg",
                      "image_width":250,
                      "image_height":250
                   },
                   "small":{
                      "url":"https://robertsspaceindustries.com/imager/b0d3P8w4T5rRViTtfP-D4hDBH9A=/fit-in/400x224/https://i.imgur.com/CZhdJhI.jpg",
                      "image_width":400,
                      "image_height":111
                   },
                   "medium":{
                      "url":"https://robertsspaceindustries.com/imager/hGC62zEXeKJtWTbdcZIiAEwVaBs=/fit-in/400x400/https://i.imgur.com/CZhdJhI.jpg",
                      "image_width":400,
                      "image_height":199
                   },
                   "large":{
                      "url":"https://robertsspaceindustries.com/imager/EKZBmnoJO18iQjyrAI_blZnude0=/fit-in/1680x1050/https://i.imgur.com/CZhdJhI.jpg",
                      "image_width":1680,
                      "image_height":524
                   }
                }
             }
          }
      },
    }
    ```
    """

    def __init__(self, client: 'httpclient.HTTPClient', payload: dict):
        self._client = client
        self.id: int = int(payload['id'])
        self.time_created: datetime = datetime.utcfromtimestamp(payload['time_created'])
        self.time_modified: datetime = datetime.utcfromtimestamp(payload['time_modified']) if payload[
            'time_modified'] else None
        self._member_id: int = int(payload['member_id'])
        # self.is_erased = payload['is_erased']
        # self.erased_by = payload['erased_by']
        self._lobby_id: int = int(payload['lobby_id'])
        self.plaintext: str = payload['plaintext']
        self.content_state: ContentState = ContentState(**payload['content_state'])
        self.media: Optional[Media] = None
        if payload.get('media'):
            self.media = Media(**payload['media'])

    @property
    def author(self) -> 'member.Member':
        return self._client.get_member(self._member_id)

    @property
    def lobby(self) -> 'lobby.Lobby':
        return self._client.get_lobby(self._lobby_id)

    def __repr__(self):
        return f"Message(id={repr(self.id)}, plaintext={repr(self.plaintext)}, author={repr(self.author)}, lobby={repr(self.lobby)})"
