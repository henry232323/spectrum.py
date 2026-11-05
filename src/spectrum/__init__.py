from ._version import __version__
from .client import Client
from .httpclient import HTTPClient
from .content_builder import ContentBuilder
from .models import *
from .errors import *

from . import client
from . import models
from . import errors
from . import util

# Sub-clients for other RSI sites. Each one is imported on its own, so a missing
# optional dependency (``aiographql-client`` for the Community Hub and Store
# GraphQL clients, installed with ``pip install spectrum.py[community-hub]``)
# only hides the clients that need it.
try:
    from . import community
    from .community import CommunityHubClient
except ImportError:
    pass

try:
    from . import store
    from .store import StoreClient
except ImportError:
    pass

from . import galactapedia
from .galactapedia import GalactapediaClient
from . import cig
from .cig import CIGClient
from . import issue_council
from .issue_council import IssueCouncilClient
from . import orgs
from .orgs import OrgsClient
from . import starmap
from .starmap import StarmapClient
from . import roadmap
from .roadmap import RoadmapClient
from . import rsi
from .rsi import RSIClient

