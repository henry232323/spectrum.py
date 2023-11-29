from .. import client


class Member:
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
        pass

    def __repr__(self):
        return f"Member()"
