import asyncio

from aiographql.client import GraphQLClient, GraphQLRequest

COMMUNITY_HUB_GRAPHQL_ENDPOINT = "https://robertsspaceindustries.com/community-hub/api/v1/graphql"


class CommunityHubClient:
    def __init__(self):
        self._client = GraphQLClient(
            endpoint=COMMUNITY_HUB_GRAPHQL_ENDPOINT,
        )

    async def fetch_user_profile(self, profile: str):
        request = GraphQLRequest(
            query='query getAccount($CreatorQuery: CreatorQuery!) {\n  creator(query: $CreatorQuery) {\n    ...Account\n    __typename\n  }\n}\n\nfragment Account on Account {\n  bio\n  citizenDossierUrl\n  displayName\n  live\n  nickname\n  stats {\n    ...AccountStats\n    __typename\n  }\n  thumbnailUrl\n  website\n  __typename\n}\n\nfragment AccountStats on AccountStats {\n  followed\n  followedCount\n  followingCount\n  upvotesCount\n  viewsCount\n  __typename\n}',
            variables={"CreatorQuery": {"nickname": "Khuzdul"}},
            operation="getAccount",
            validate=False
        )
        resp = await self._client.query(request=request)
        return resp.data
