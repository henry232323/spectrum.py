from . import lobby
from .. import client


class Message:
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
      },
    }
    ```
    """

    def __init__(self, client: 'client.Client', payload: dict):
        self._client = client
        self.id = payload['message']['id']
        self.time_created = payload['message']['time_created']
        self.time_modified = payload['message']['time_modified']
        self._member_id = payload['message']['member_id']
        # self.is_erased = payload['message']['is_erased']
        # self.erased_by = payload['message']['erased_by']
        self._lobby_id = payload['message']['lobby_id']
        self.content = payload['message']['plaintext']

    @property
    def author(self):
        return self._client.get_member(self._member_id)

    @property
    def lobby(self) -> 'lobby.Lobby':
        return self._client.get_lobby(self._lobby_id)

    def __repr__(self):
        return f"Message(id={repr(self.id)}, content={repr(self.content)}, author={repr(self.author)}, lobby={repr(self.lobby)})"
