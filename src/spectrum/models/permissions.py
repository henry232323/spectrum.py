import dataclasses


@dataclasses.dataclass
class GlobalPermissions:
    manage_roles: bool
    kick_members: bool
    embed_link: bool
    upload_media: bool
    mention: bool
    reaction: bool
    vote: bool
    read_erased: bool


@dataclasses.dataclass
class MessageLobbyPermissions:
    read: bool
    send_message: bool
    manage: bool
    moderate: bool
    set_motd: bool


@dataclasses.dataclass
class ForumChannelPermissions:
    read: bool
    create_thread: bool
    create_thread_reply: bool
    manage: bool
    moderate: bool


@dataclasses.dataclass
class CustomEmojiPermissions:
    create: bool
    remove: bool

@dataclasses.dataclass
class Permissions:
    global_: GlobalPermissions
    message_lobby: MessageLobbyPermissions
    forum_channel: ForumChannelPermissions
    custom_emoji: CustomEmojiPermissions

    @classmethod
    def from_payload(cls, payload):
        dupe = payload.copy()
        dupe['global_'] = dupe['global']
        del dupe['global']

        return cls(**dupe)

    def __post_init__(self):
        self.global_ = GlobalPermissions(**self.global_)
        self.message_lobby = MessageLobbyPermissions(**self.message_lobby)
        self.forum_channel = ForumChannelPermissions(**self.forum_channel)
        self.custom_emoji = CustomEmojiPermissions(**self.custom_emoji)
