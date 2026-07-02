"""
Spectrum MCP Server — local testing tool for interacting with RSI Spectrum via Claude.

Usage:
  1. Set RSI_TOKEN and DEVICE_ID env vars (or create a .env file)
  2. Run: python mcp_server.py
  3. Configure Claude Code to connect to this server (stdio transport)
"""

import json
import os
import sys
from pathlib import Path

# Load .env from project root
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# Suppress all logging to stderr
import logging
logging.disable(logging.CRITICAL)

# Add src to path so we can import spectrum
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mcp.server.fastmcp import FastMCP
from spectrum import HTTPClient

# Global client instance
_client: HTTPClient | None = None


async def get_client() -> HTTPClient:
    global _client
    if _client is None:
        token = os.environ.get("RSI_TOKEN")
        device_id = os.environ.get("DEVICE_ID")
        if not token or not device_id:
            raise RuntimeError("RSI_TOKEN and DEVICE_ID environment variables are required")
        _client = HTTPClient(rsi_token=token, device_id=device_id)
        await _client.identify()
    return _client


mcp = FastMCP("spectrum-mcp")


@mcp.tool()
async def spectrum_identify() -> str:
    """Authenticate and identify the current user. Returns info about the logged-in member, their communities, and lobbies."""
    client = await get_client()
    member = client.me
    communities = [{"id": c.id, "name": c.name, "slug": c.slug} for c in client.communities]
    lobbies = [{"id": l.id, "name": l.name, "community_id": l.community_id} for l in client.lobbies]
    return json.dumps({
        "member": {"id": member.id, "displayname": member.displayname, "nickname": member.nickname},
        "communities": communities,
        "lobbies": lobbies[:20],
    }, indent=2)


@mcp.tool()
async def spectrum_fetch_member(handle: str = None, member_id: int = None) -> str:
    """Fetch a Spectrum member by handle (username) or numeric ID."""
    client = await get_client()
    if handle:
        member = await client.fetch_member_by_handle(handle)
    elif member_id:
        member = await client.fetch_member_by_id(member_id)
    else:
        return json.dumps({"error": "Provide either 'handle' or 'member_id'"})
    if member is None:
        return json.dumps({"error": "Member not found"})
    return json.dumps({
        "id": member.id,
        "displayname": member.displayname,
        "nickname": member.nickname,
        "avatar_url": member.avatar_url,
        "signature": member.signature,
        "badges": [{"name": b.name} for b in (member.badges or [])],
    }, indent=2)


@mcp.tool()
async def spectrum_search_users(query: str, max_count: int = 10) -> str:
    """Search for Spectrum users by query string."""
    client = await get_client()
    results = []
    async for member in client.search_users(query, max_count=max_count):
        results.append({
            "id": member.id,
            "displayname": member.displayname,
            "nickname": member.nickname,
        })
    return json.dumps(results, indent=2)


@mcp.tool()
async def spectrum_list_communities() -> str:
    """List all communities the authenticated user belongs to."""
    client = await get_client()
    communities = [{
        "id": c.id,
        "name": c.name,
        "slug": c.slug,
        "lobbies_count": len(c.lobbies) if c.lobbies else 0,
        "forums_count": len(c.forums) if c.forums else 0,
    } for c in client.communities]
    return json.dumps(communities, indent=2)


@mcp.tool()
async def spectrum_list_lobbies(community_id: int = None) -> str:
    """List chat lobbies, optionally filtered by community ID."""
    client = await get_client()
    lobbies = client.lobbies
    if community_id:
        lobbies = [l for l in lobbies if l.community_id == community_id]
    result = [{
        "id": l.id,
        "name": l.name,
        "community_id": l.community_id,
        "type": l.type,
        "description": l.description,
    } for l in lobbies]
    return json.dumps(result, indent=2)


@mcp.tool()
async def spectrum_list_forums(community_id: int = 1) -> str:
    """List forum groups and their channels for a community."""
    client = await get_client()
    community = client.get_community(community_id)
    if not community:
        return json.dumps({"error": f"Community {community_id} not found"})
    forums = []
    for forum in (community.forums or []):
        channels = [{
            "id": ch.id,
            "name": ch.name,
            "description": ch.description,
            "threads_count": ch.threads_count,
        } for ch in (forum.channels or [])]
        forums.append({"id": forum.id, "name": forum.name, "channels": channels})
    return json.dumps(forums, indent=2)


@mcp.tool()
async def spectrum_fetch_lobby_history(lobby_id: int, count: int = 20) -> str:
    """Fetch recent message history from a lobby (chat room or DM)."""
    client = await get_client()
    lobby = client.get_lobby(lobby_id)
    if not lobby:
        lobby = await client.fetch_lobby(lobby_id)
    if not lobby:
        return json.dumps({"error": "Lobby not found"})
    messages = []
    async for msg in lobby.fetch_history(count=count):
        messages.append({
            "id": msg.id,
            "author": msg.author.displayname if msg.author else "Unknown",
            "content": msg.plaintext,
            "time_created": str(msg.time_created) if msg.time_created else None,
        })
    return json.dumps(messages, indent=2)


@mcp.tool()
async def spectrum_send_message(lobby_id: int, content: str) -> str:
    """Send a message to a lobby (chat room or DM)."""
    client = await get_client()
    lobby = client.get_lobby(lobby_id)
    if not lobby:
        lobby = await client.fetch_lobby(lobby_id)
    if not lobby:
        return json.dumps({"error": "Lobby not found"})
    msg = await lobby.send(content)
    return json.dumps({
        "id": msg.id,
        "content": msg.plaintext,
        "lobby_id": lobby.id,
    }, indent=2)


@mcp.tool()
async def spectrum_send_dm(content: str, handle: str = None, member_id: int = None) -> str:
    """Send a direct message to a member by handle or ID."""
    client = await get_client()
    if handle:
        member = await client.fetch_member_by_handle(handle)
    elif member_id:
        member = await client.fetch_member_by_id(member_id)
    else:
        return json.dumps({"error": "Provide either 'handle' or 'member_id'"})
    if not member:
        return json.dumps({"error": "Member not found"})
    msg = await member.send(content)
    return json.dumps({
        "id": msg.id,
        "content": msg.plaintext,
        "recipient": member.displayname,
    }, indent=2)


@mcp.tool()
async def spectrum_search_content(text: str, community_id: int = 1, sort: str = "latest",
                                   content_types: list[str] = None, author: str = None,
                                   page: int = 1) -> str:
    """Search posts, replies, and messages across Spectrum."""
    client = await get_client()
    results = await client.search_content(
        community_id=str(community_id),
        text=text,
        sort=sort,
        content_types=content_types,
        author=author,
        page=page,
    )
    items = []
    for r in results:
        item = {"type": getattr(r, "type", None)}
        if hasattr(r, "subject"):
            item["subject"] = r.subject
        if hasattr(r, "plaintext"):
            item["content"] = r.plaintext[:500] if r.plaintext else None
        if hasattr(r, "id"):
            item["id"] = r.id
        if hasattr(r, "member") and r.member:
            item["author"] = r.member.displayname if hasattr(r.member, "displayname") else str(r.member)
        items.append(item)
    return json.dumps(items, indent=2)


@mcp.tool()
async def spectrum_fetch_thread(thread_id: int) -> str:
    """Fetch a forum thread by ID, including its replies."""
    client = await get_client()
    thread = client.get_thread(thread_id)
    if not thread:
        return json.dumps({"error": "Thread not found — it may need to be fetched via channel listing first"})
    replies = []
    for reply in (thread.replies or [])[:50]:
        replies.append({
            "id": reply.id,
            "author": reply.member.displayname if reply.member else "Unknown",
            "content": reply.content_blocks[0].plaintext() if reply.content_blocks else "",
            "time_created": str(reply.time_created) if reply.time_created else None,
            "votes": reply.votes,
        })
    content = ""
    if thread.content_blocks:
        content = thread.content_blocks[0].plaintext() if thread.content_blocks else ""
    return json.dumps({
        "id": thread.id,
        "subject": thread.subject,
        "author": thread.member.displayname if thread.member else "Unknown",
        "content": content,
        "replies_count": thread.replies_count,
        "views_count": thread.views_count,
        "votes": thread.votes,
        "is_locked": thread.is_locked,
        "is_pinned": thread.is_pinned,
        "replies": replies,
    }, indent=2)


@mcp.tool()
async def spectrum_list_threads(channel_id: int, max_count: int = 20) -> str:
    """List threads in a forum channel."""
    client = await get_client()
    channel = client.get_channel(channel_id)
    if not channel:
        return json.dumps({"error": "Channel not found"})
    threads = []
    stubs = await channel.fetch_thread_stubs(max_count=max_count)
    for stub in stubs:
        threads.append({
            "id": stub.id,
            "subject": stub.subject,
            "author": stub.member.displayname if stub.member else "Unknown",
            "replies_count": stub.replies_count,
            "views_count": stub.views_count,
            "votes": stub.votes,
            "time_created": str(stub.time_created) if stub.time_created else None,
            "is_pinned": stub.is_pinned,
            "is_locked": stub.is_locked,
        })
    return json.dumps(threads, indent=2)


@mcp.tool()
async def spectrum_create_thread(channel_id: int, subject: str, content: str,
                                  type: str = "discussion",
                                  content_blocks: list[dict] = None,
                                  highlight_role_id: str = None,
                                  is_locked: bool = False,
                                  is_reply_nesting_disabled: bool = False) -> str:
    """Create a new forum thread in a channel. For rich content with images, pass content_blocks directly (list of block dicts with type 'text' or 'image'). Image blocks use format: {"id": "unique-id", "type": "image", "data": ["upload:XXXXX"]}. Text blocks use Draft.js format. The 'content' param is used as plaintext fallback and for the plaintext field."""
    client = await get_client()
    channel = client.get_channel(channel_id)
    if not channel:
        return json.dumps({"error": "Channel not found"})
    thread = await channel.create_thread(
        subject=subject,
        plaintext=content,
        type=type,
        content_blocks=content_blocks,
        highlight_role_id=highlight_role_id,
        is_locked=is_locked,
        is_reply_nesting_disabled=is_reply_nesting_disabled,
    )
    return json.dumps({
        "id": thread.id,
        "subject": thread.subject,
        "slug": thread.slug,
    }, indent=2)


@mcp.tool()
async def spectrum_fetch_community_members(community_id: int = 1, page: int = 1,
                                            pagesize: int = 12) -> str:
    """Fetch members of a community with pagination."""
    client = await get_client()
    community = client.get_community(community_id)
    if not community:
        return json.dumps({"error": "Community not found"})
    result = await community.fetch_members(page=page, pagesize=pagesize)
    members = [{
        "id": m.id,
        "displayname": m.displayname,
        "nickname": m.nickname,
    } for m in result.items]
    return json.dumps({
        "members": members,
        "total": result.total,
        "page": result.page,
        "pages_total": result.pages_total,
    }, indent=2)


@mcp.tool()
async def spectrum_set_status(status: str, info: str = None) -> str:
    """Set the authenticated user's presence status."""
    client = await get_client()
    await client.set_status(status, info=info)
    return json.dumps({"status": "ok", "set_to": status})


@mcp.tool()
async def spectrum_upload_image(file_path: str) -> str:
    """Upload an image to Spectrum. Returns media data (id, slug, type) for embedding in posts."""
    client = await get_client()
    result = await client.upload_image(file_path)
    return json.dumps(result, indent=2)


@mcp.tool()
async def spectrum_fetch_embed(url: str) -> str:
    """Fetch embed data for a URL (videos, articles). Returns rich embed metadata for use in posts."""
    client = await get_client()
    result = await client.fetch_embed(url)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
