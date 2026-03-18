"""Tests for MCP Server — 4 pure-data tools, no LLM."""

import json

import pytest
from fastmcp import Client


@pytest.fixture
def mcp_client(minimal_pack):
    from docchat.mcp_server import create_mcp_server

    mcp = create_mcp_server(minimal_pack)
    return Client(mcp)


@pytest.mark.asyncio
async def test_list_tools(mcp_client):
    async with mcp_client:
        tools = await mcp_client.list_tools()
        tool_names = [t.name for t in tools]
        assert "list_feeds" in tool_names
        assert "search_by_field" in tool_names
        assert "get_feed_info" in tool_names
        assert "route_question" in tool_names
        assert "ask_api_expert" not in tool_names


@pytest.mark.asyncio
async def test_list_feeds(mcp_client):
    async with mcp_client:
        result = await mcp_client.call_tool("list_feeds", {})
        data = json.loads(result.content[0].text)
        codes = [f["feed_code"] for f in data]
        assert "get-users" in codes
        assert "get-posts" in codes


@pytest.mark.asyncio
async def test_route_question(mcp_client):
    async with mcp_client:
        result = await mcp_client.call_tool(
            "route_question", {"query": "get user list"}
        )
        data = json.loads(result.content[0].text)
        assert len(data["matched_feeds"]) > 0
        codes = [f[0] for f in data["matched_feeds"]]
        assert "get-users" in codes


@pytest.mark.asyncio
async def test_route_question_overview(mcp_client):
    async with mcp_client:
        result = await mcp_client.call_tool(
            "route_question", {"query": "有哪些接口"}
        )
        data = json.loads(result.content[0].text)
        assert data["routing_method"] == "deterministic:overview"


@pytest.mark.asyncio
async def test_get_feed_info(mcp_client):
    async with mcp_client:
        result = await mcp_client.call_tool(
            "get_feed_info", {"feed_code": "get-users"}
        )
        data = json.loads(result.content[0].text)
        assert data["feed_code"] == "get-users"
        assert "GET /api/users" in data["knowledge"]


@pytest.mark.asyncio
async def test_get_feed_info_not_found(mcp_client):
    async with mcp_client:
        result = await mcp_client.call_tool(
            "get_feed_info", {"feed_code": "nonexistent"}
        )
        data = json.loads(result.content[0].text)
        assert "error" in data


@pytest.mark.asyncio
async def test_search_by_field(mcp_client):
    async with mcp_client:
        result = await mcp_client.call_tool(
            "search_by_field", {"field_name": "userId"}
        )
        data = json.loads(result.content[0].text)
        assert len(data) > 0
        assert data[0]["feed_code"] == "get-users"


@pytest.mark.asyncio
async def test_api_expert_prompt_includes_tool_guidance(mcp_client):
    async with mcp_client:
        prompts = await mcp_client.list_prompts()
        prompt_names = [p.name for p in prompts]
        assert "api_expert_system" in prompt_names

        result = await mcp_client.get_prompt("api_expert_system")
        prompt_text = result.messages[0].content.text
        assert "MCP Tool Usage Best Practices" in prompt_text
        assert "route_question" in prompt_text
        assert "Never fabricate" in prompt_text
