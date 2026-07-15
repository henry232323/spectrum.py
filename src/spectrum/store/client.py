from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from aiographql.client import GraphQLClient, GraphQLRequest

STORE_GRAPHQL_ENDPOINT = "https://robertsspaceindustries.com/graphql"
GRAPHQL_DIR = Path(__file__).parent / "graphql"


def _load_query(category: str, name: str) -> str:
    path = GRAPHQL_DIR / category / f"{name}.graphql"
    return path.read_text()


@dataclass
class Ship:
    id: int = 0
    name: str = ""
    focus: str = ""
    type: str = ""
    flyableStatus: str = ""
    owned: bool = False
    msrp: int = 0
    link: str = ""
    medias: Optional[dict] = None
    manufacturer: Optional[dict] = None
    skus: list[dict] = field(default_factory=list)


@dataclass
class ShipSku:
    id: int = 0
    title: str = ""
    price: int = 0
    upgradePrice: int = 0
    available: bool = False
    unlimitedStock: bool = False
    availableStock: int = 0
    body: str = ""
    showStock: bool = False


@dataclass
class Manufacturer:
    id: int = 0
    name: str = ""


@dataclass
class Pricing:
    currencyCode: str = ""
    currencySymbol: str = ""
    exchangeRate: float = 1.0
    exponent: int = 2
    taxRate: float = 0.0
    isTaxInclusive: bool = False


class StoreClient:
    """Client for the RSI Pledge Store GraphQL API."""

    def __init__(self, rsi_token: str | None = None, device_id: str | None = None):
        headers = {"content-type": "application/json"}
        if rsi_token:
            headers["x-rsi-token"] = rsi_token
            headers["cookie"] = f"Rsi-Token={rsi_token}"
            if device_id:
                headers["cookie"] += f"; _rsi_device={device_id}"

        self._client = GraphQLClient(endpoint=STORE_GRAPHQL_ENDPOINT, headers=headers)

    @classmethod
    def from_client(cls, client) -> StoreClient:
        """Create a StoreClient using auth from an existing HTTPClient/Client."""
        return cls(rsi_token=client._http._rsi_token, device_id=client._http._device_id)

    async def _execute(self, query: str, variables: dict | None = None, operation: str | None = None) -> dict:
        request = GraphQLRequest(query=query, variables=variables or {}, operation=operation, validate=False)
        resp = await self._client.query(request=request)
        return resp.data

    # --- Account ---

    async def fetch_account(self) -> dict:
        """Fetch basic account info (anonymous status)."""
        query = _load_query("queries", "AccountQuery")
        data = await self._execute(query, {}, "AccountQuery")
        return data.get("account", {})

    async def fetch_account_badges(self) -> list[dict]:
        """Fetch account badges."""
        query = _load_query("queries", "AccountBadgesQuery")
        data = await self._execute(query, {}, "AccountBadgesQuery")
        return data.get("account", {}).get("badges", [])

    # --- Store Catalog ---

    async def fetch_collection(self, slug: str) -> dict:
        """Fetch a store collection by slug."""
        query = _load_query("queries", "CollectionQuery")
        data = await self._execute(query, {"slug": slug}, "CollectionQuery")
        return data.get("collection", {})

    async def fetch_featured_sku(self) -> dict:
        """Fetch the featured SKU on the store."""
        query = _load_query("queries", "FeaturedSkuQuery")
        data = await self._execute(query, {}, "FeaturedSkuQuery")
        return data.get("featuredSku", {})

    async def fetch_personalization_modal(self) -> dict:
        """Fetch personalization options for the store."""
        query = _load_query("queries", "PersonalizationModalQuery")
        data = await self._execute(query, {}, "PersonalizationModalQuery")
        return data

    # --- Ship Upgrades ---
    # Note: These queries require the ship upgrade page context on the RSI site.
    # They may return empty results when called standalone.

    async def fetch_ship_upgrades(self) -> dict:
        """Fetch available ships for CCU/upgrades, manufacturers, and pricing info."""
        query = _load_query("queries", "initShipUpgrade")
        data = await self._execute(query, {}, "initShipUpgrade")
        return data

    async def filter_ships(self, *, from_id: int | None = None, to_id: int | None = None,
                           from_filters: list[dict] | None = None,
                           to_filters: list[dict] | None = None) -> dict:
        """Filter available ship upgrades by source and target ship."""
        query = _load_query("queries", "filterShips")
        variables = {}
        if from_id is not None:
            variables["fromId"] = from_id
        if to_id is not None:
            variables["toId"] = to_id
        if from_filters:
            variables["fromFilters"] = from_filters
        if to_filters:
            variables["toFilters"] = to_filters
        data = await self._execute(query, variables, "filterShips")
        return data

    async def fetch_upgrade_filters(self) -> dict:
        """Fetch available filter options for ship upgrades."""
        query = _load_query("queries", "filters")
        data = await self._execute(query, {}, "filters")
        return data

    async def get_upgrade_price(self, from_id: int, to_id: int) -> dict:
        """Get the price for a specific ship upgrade path."""
        query = _load_query("queries", "getPrice")
        data = await self._execute(query, {"fromId": from_id, "toId": to_id}, "getPrice")
        return data.get("price", {})

    # --- Rewards ---

    async def fetch_rewards(self) -> dict:
        """Fetch available rewards/referral rewards."""
        query = _load_query("queries", "GetRewardsQuery")
        data = await self._execute(query, {}, "GetRewardsQuery")
        return data.get("rewards", {})

    async def redeem_reward(self, code: str) -> dict:
        """Redeem a reward code."""
        query = _load_query("mutations", "RedeemRewardQuery")
        data = await self._execute(query, {"code": code}, "RedeemRewardQuery")
        return data.get("redeemReward", {})
