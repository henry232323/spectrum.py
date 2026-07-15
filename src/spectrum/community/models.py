from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AccountStats:
    followed: bool = False
    followedCount: int = 0
    followingCount: int = 0
    upvotesCount: int = 0
    viewsCount: int = 0


@dataclass
class Account:
    nickname: str = ""
    displayName: str = ""
    bio: str = ""
    citizenDossierUrl: str = ""
    live: Optional[dict] = None
    thumbnailUrl: str = ""
    website: str = ""
    stats: Optional[AccountStats] = None

    def __post_init__(self):
        if isinstance(self.stats, dict):
            self.stats = AccountStats(**self.stats)


@dataclass
class AccountCard:
    nickname: str = ""
    displayName: str = ""
    live: Optional[dict] = None
    thumbnailUrl: str = ""


@dataclass
class Badge:
    slug: str = ""
    title: str = ""
    uid: str = ""


@dataclass
class ConnectedAccountData:
    nickname: str = ""
    displayName: str = ""
    bio: str = ""
    citizenDossierUrl: str = ""
    live: Optional[dict] = None
    thumbnailUrl: str = ""
    twitchUserId: Optional[str] = None
    uid: str = ""
    website: str = ""
    probationUntil: Optional[str] = None
    badges: list[Badge] = field(default_factory=list)
    stats: Optional[AccountStats] = None

    def __post_init__(self):
        if isinstance(self.stats, dict):
            self.stats = AccountStats(**self.stats)
        self.badges = [Badge(**b) if isinstance(b, dict) else b for b in self.badges]


@dataclass
class Tag:
    label: str = ""
    slug: str = ""
    uid: str = ""


@dataclass
class Settings:
    firstConnection: bool = False
    homeLive: bool = False
    homeTags: list[Tag] = field(default_factory=list)
    postSortDiscover: Optional[str] = None
    postSortHome: Optional[str] = None
    postSortLivestream: Optional[str] = None
    postSortProfile: Optional[str] = None
    videoAutoplayCarousel: bool = False
    videoAutoplayPostDetail: bool = False
    videoAutoplayProfile: bool = False

    def __post_init__(self):
        self.homeTags = [Tag(**t) if isinstance(t, dict) else t for t in self.homeTags]


@dataclass
class Media:
    uid: str = ""
    type: str = ""
    url: str = ""
    caption: Optional[str] = None
    fullsize: Optional[str] = None
    gallerylarge: Optional[str] = None
    gallerysmall: Optional[str] = None
    large: Optional[str] = None
    placeholder: Optional[str] = None
    thumbnail: Optional[str] = None
    wide: Optional[str] = None


@dataclass
class Ship:
    id: str = ""
    name: str = ""


@dataclass
class Manufacturer:
    id: str = ""
    name: str = ""
    code: str = ""
    icon: str = ""
    logo: str = ""
    status: str = ""


@dataclass
class EventGroup:
    mandatoryShipTagging: bool = False
    slug: str = ""
    title: str = ""
    uid: str = ""


@dataclass
class Event:
    uid: str = ""
    title: str = ""
    slug: str = ""
    description: str = ""
    summary: str = ""
    label: Optional[str] = None
    url: Optional[str] = None
    startedAt: Optional[str] = None
    endedAt: Optional[str] = None
    isLive: bool = False
    postCount: int = 0
    contestTitle: Optional[str] = None
    contestUrl: Optional[str] = None
    eventGroup: Optional[EventGroup] = None
    media: list[Media] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.eventGroup, dict):
            self.eventGroup = EventGroup(**self.eventGroup)
        self.media = [Media(**m) if isinstance(m, dict) else m for m in self.media]


@dataclass
class Annotation:
    body: str = ""
    date: Optional[str] = None


@dataclass
class Voter:
    nickname: str = ""
    displayName: str = ""
    thumbnailUrl: str = ""


@dataclass
class Post:
    """Base post model covering Text, Image, Video, Audio, Live types."""
    uid: str = ""
    type: str = ""
    title: str = ""
    slug: str = ""
    summary: str = ""
    body: str = ""
    status: str = ""
    honor: bool = False
    contest: Optional[str] = None
    createdAt: Optional[str] = None
    modifiedAt: Optional[str] = None
    modifiedBy: Optional[str] = None
    commentsCount: int = 0
    viewsCount: int = 0
    votesCount: int = 0
    voted: bool = False
    reported: bool = False
    reportsCount: int = 0
    duration: Optional[int] = None
    viewersCount: Optional[int] = None
    membershipProvider: Optional[str] = None
    membershipUrl: Optional[str] = None
    annotation: Optional[Annotation] = None
    account: Optional[Account] = None
    event: Optional[Event] = None
    media: list[Media] = field(default_factory=list)
    tags: list[Tag] = field(default_factory=list)
    ships: list[Ship] = field(default_factory=list)
    voters: list[Voter] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.annotation, dict):
            self.annotation = Annotation(**self.annotation)
        if isinstance(self.account, dict):
            self.account = Account(**self.account)
        if isinstance(self.event, dict):
            self.event = Event(**self.event)
        self.media = [Media(**m) if isinstance(m, dict) else m for m in self.media]
        self.tags = [Tag(**t) if isinstance(t, dict) else t for t in self.tags]
        self.ships = [Ship(**s) if isinstance(s, dict) else s for s in self.ships]
        self.voters = [Voter(**v) if isinstance(v, dict) else v for v in self.voters]


@dataclass
class PostCard:
    """Lightweight post for list views."""
    uid: str = ""
    type: str = ""
    title: str = ""
    slug: str = ""
    summary: str = ""
    status: str = ""
    honor: bool = False
    createdAt: Optional[str] = None
    commentsCount: int = 0
    viewsCount: int = 0
    votesCount: int = 0
    voted: bool = False
    thumbnailUrl: Optional[str] = None
    account: Optional[AccountCard] = None
    event: Optional[dict] = None
    tags: list[Tag] = field(default_factory=list)
    voters: list[Voter] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.account, dict):
            self.account = AccountCard(**self.account)
        self.tags = [Tag(**t) if isinstance(t, dict) else t for t in self.tags]
        self.voters = [Voter(**v) if isinstance(v, dict) else v for v in self.voters]


@dataclass
class Comment:
    uid: str = ""
    body: str = ""
    createdAt: Optional[str] = None
    modifiedAt: Optional[str] = None
    parentUid: Optional[str] = None
    repliesCount: int = 0
    votesCount: int = 0
    voted: bool = False
    reported: bool = False
    reportsCount: int = 0
    annotation: Optional[Annotation] = None
    account: Optional[AccountCard] = None

    def __post_init__(self):
        if isinstance(self.annotation, dict):
            self.annotation = Annotation(**self.annotation)
        if isinstance(self.account, dict):
            self.account = AccountCard(**self.account)


@dataclass
class PaginatedResult:
    """Generic paginated response wrapper."""
    metaData: list = field(default_factory=list)
    totalCount: int = 0
    hasNextPage: bool = False
