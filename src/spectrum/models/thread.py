from datetime import datetime

from . import abc
from .activity import Activity
from .content import ContentBlock
from .. import httpclient


class Thread(abc.Identifier, abc.Subscription):
    """
    {
        "data": {
            "id": "395818",
            "time_created": 1701202141,
            "time_modified": 1701295558,
            "channel_id": "3",
            "label_id": "",
            "type": "discussion",
            "slug": "galactapedia-update-november-28-2023",
            "subject": "Galactapedia Update | November 28, 2023",
            "is_locked": false,
            "is_reply_nesting_disabled": false,
            "is_pinned": true,
            "is_sinked": false,
            "is_erased": false,
            "erased_by": null,
            "tracked_post_role_id": "2",
            "content_reply_id": "6446307",
            "annotation_plaintext": null,
            "subscription_key": "community:1:forum_thread:395818:b5775a5f61ca546e3c529bd0a7c9b77292b20223",
            "content_blocks": [
                {
                    "id": 1,
                    "type": "text",
                    "data": {
                        "blocks": [
                            {
                                "key": "9iqi5",
                                "text": "Happy Tuesday!",
                                "type": "unstyled",
                                "depth": 0,
                                "inlineStyleRanges": [],
                                "entityRanges": [],
                                "data": []
                            },
                        ]
                    }
                }
            ],
            "highlight_role_id": "2",
            "community_id": "1",
            "member": [ Member ],
            "replies_count": 10,
            "views_count": 728,
            "latest": 6450512,
            "latest_activity": {
                "time_created": 1701295558,
                "member": [ Member ],
                "highlight_role_id": null
            },
            "newest_unread": null,
            "last_read": null,
            "last_marker": null,
            "votes": {
                "count": 31,
                "voted": 0
            },
            "reactions": [
                {
                    "type": ":heart:",
                    "count": 7,
                    "members": {
                        "74": "Ozimundi",
                        "12259": "Maverrick",
                        "72981": "Shiwaz",
                        "132086": "Lannar",
                        "133205": "MrTrash",
                        "3641515": "EverlastOG",
                        "3744493": "Flooficus"
                    }
                },
            ],
            "tracked_replies_references": [],
            "children_replies_references": [],
            "notification_subscription": null,
            "aspect": "full",
            "nested_replies_ids": [
                "6446399",
                "6446387",
                "6446389",
                "6447785",
                "6446431",
                "6447399",
                "6447791",
                "6448124",
                "6450512",
                "6447416"
            ],
            "replies": [
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
            ]
        }
    }
    """

    def __init__(self, client: 'httpclient.HTTPClient', payload: dict):
        self._client = client
        self.id = int(payload["id"])
        self.time_created = datetime.utcfromtimestamp(payload["time_created"])
        self.time_modified = datetime.utcfromtimestamp(payload["time_modified"]) if payload["time_modified"] else None

        self.channel_id = int(payload["channel_id"])
        self.community_id = int(payload["community_id"])
        self.label_id = int(payload["label_id"])

        self.type = payload["type"]
        self.slug = payload["slug"]
        self.subject = payload["subject"]

        self.is_locked = payload["is_locked"]
        self.is_reply_nesting_disabled = payload["is_reply_nesting_disabled"]
        self.is_pinned = payload["is_pinned"]
        self.is_sinked = payload["is_sinked"]
        self.is_erased = payload["is_erased"]
        self.erased_by = payload["erased_by"]

        self.tracked_post_role_id = int(payload["tracked_post_role_id"])
        self.content_reply_id = int(payload["content_reply_id"])

        self.annotation_plaintext = payload["annotation_plaintext"]
        self.subscription_key = payload["subscription_key"]
        self.content_blocks = [ContentBlock(**data) for data in payload["content_blocks"]]
        self.highlight_role_id = int(payload["highlight_role_id"])

        self.member = self._client._replace_member(payload["member"])

        self.replies_count = payload["replies_count"]
        self.views_count = payload["views_count"]
        self.latest = payload["latest"]
        self.latest_activity = Activity(**payload["latest_activity"])
        self.newest_unread = payload["newest_unread"]
        self.last_read = payload["last_read"]
        self.last_marker = payload["last_marker"]
        self.votes = payload["votes"]
        self.reactions = payload["reactions"]
        self.tracked_replies_references = payload["tracked_replies_references"]
        self.children_replies_references = payload["children_replies_references"]
        self.notification_subscription = payload["notification_subscription"]
        self.aspect = payload["aspect"]
        self.nested_replies_ids = [int(x) for x in payload["nested_replies_ids"]]
        self.replies = payload["replies"]

    @property
    def channel(self):
        return self._client.get_channel(self.channel_id)

    @property
    def community(self):
        return self._client.get_community(self.community_id)

    async def sink(self):
        return await self._client.sink_threads(self)

    async def pin(self):
        return await self._client.pin_threads(self)

    async def close(self):
        return await self._client.close_threads(self)

    async def delete(self):
        return await self._client.delete_threads(self)

    async def add_vote(self):
        await self._client._http.add_vote({
            "entity_type": "forum_thread",
            "entity_id": self.id
        })

    async def remove_vote(self):
        await self._client._http.remove_vote({
            "entity_type": "forum_thread",
            "entity_id": self.id
        })
