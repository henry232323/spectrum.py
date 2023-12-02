from . import abc
from .presence import Presence
from .. import client


class Member(abc.Identifier):
    """
    {
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
    }
    """

    def __init__(self, client: 'client.Client', payload: dict):
        self._client = client
        self.id = payload["id"]
        self.displayname = payload["displayname"]
        self.nickname = payload["nickname"]
        self.avatar_url = payload["avatar"]
        self.signature = payload["signature"]
        self.isGM = payload["isGM"]
        self.spoken_languages = payload["spoken_languages"]
        self.meta = payload["meta"]
        self.presence = None

        if "presence" in payload:
            self.presence = Presence(self._client, payload['presence'])

    def __repr__(self):
        return f"Member(id={repr(self.id)}, displayname={repr(self.displayname)}, nickname={repr(self.nickname)})"
