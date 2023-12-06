from datetime import datetime

from . import abc
from .. import httpclient


class Reply(abc.Identifier):
    """
    {
        "id": "6446399",
        "time_created": 1701203593,
        "time_modified": 1701203593,
        "thread_id": "395818",
        "content_blocks": [
            {
                "id": 1,
                "type": "text",
                "data": {
                    "blocks": [
                        {
                            "key": "dbos5",
                            "text": "I want another SCL with Cherie, been a long time!",
                            "type": "unstyled",
                            "depth": 0,
                            "inlineStyleRanges": [],
                            "entityRanges": [],
                            "data": []
                        }
                    ],
                    "entityMap": []
                }
            }
        ],
        "is_erased": false,
        "erased_by": null,
        "annotation_plaintext": null,
        "member": {
            "id": "213788",
            "displayname": "BrE",
            "nickname": "BrE",
            "avatar": "https://robertsspaceindustries.com/media/epnp8wif3q0oer/heap_infobox/Bre-3_Artboard_1.png?v=1660175237",
            "signature": "",
            "meta": {
                "badges": [
                    {
                        "name": "Original backer",
                        "icon": "https://robertsspaceindustries.com/media/70n5kk4hfx2rmr/heap_note/Original_backer.png"
                    },
                    {
                        "name": "Avenger Squadron",
                        "icon": "/media/dow7hpkylrdv6r/heap_note/AVSQN-Thumbnail.png",
                        "url": "https://robertsspaceindustries.com/orgs/AVSQN"
                    }
                ]
            },
            "isGM": false,
            "spoken_languages": [
                "en",
                "fr",
                "es"
            ],
            "roles": {
                "1": [
                    "11",
                    "4"
                ],
                "9711": [
                    "67976"
                ],
                "75243": [
                    "511391",
                    "511394"
                ],
                "93188": [
                    "611840"
                ]
            }
        },
        "votes": {
            "count": 11,
            "voted": 0
        },
        "reactions": [],
        "parent_reply_reference": null,
        "children_replies_references": [],
        "tracked_replies_references": [],
        "read": false,
        "replies_count": 0,
        "replies": []
    },
    """

    def __init__(self, client: 'httpclient.HTTPClient', payload: dict):
        self._client = client
        self.id = int(payload["id"])
        self.thread_id = int(payload["thread_id"])
        self.time_created = datetime.utcfromtimestamp(payload["time_created"])
        self.time_modified = datetime.utcfromtimestamp(payload["time_modified"]) if payload["time_modified"] else None
        self.content_blocks = payload["content_blocks"]
        self.is_erased = payload["is_erased"]
        self.erased_by = payload["erased_by"]
        self.annotation_plaintext = payload["annotation_plaintext"]
        self.member = self._client._replace_member(payload["member"])
        self.votes = payload["votes"]
        self.reactions = payload["reactions"]
        self.parent_reply_reference = payload["parent_reply_reference"]
        self.children_replies_references = payload["children_replies_references"]
        self.tracked_replies_references = payload["tracked_replies_references"]
        self.read = payload["read"]
        self.replies_count = payload["replies_count"]
        self.replies = payload["replies"]

    @property
    def thread(self):
        return self._client.get_thread(self.thread_id)

    async def add_vote(self):
        await self._client._http.add_vote({
            "entity_type": "forum_thread_reply",
            "entity_id": self.id
        })

    async def remove_vote(self):
        await self._client._http.remove_vote({
            "entity_type": "forum_thread_reply",
            "entity_id": self.id
        })
