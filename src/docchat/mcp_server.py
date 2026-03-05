"""MCP Server — factory function that creates a FastMCP instance from a knowledge pack.

Provides 4 pure-data Tools (no LLM):
- list_feeds: List all available feeds
- search_by_field: Search feeds by field name
- get_feed_info: Get detailed feed information + knowledge
- route_question: Route a user query to matching feeds
"""

import json
from pathlib import Path

from fastmcp import FastMCP

from docchat.engine.index_loader import KnowledgeEngine
from docchat.schema import load_pack_config


def create_mcp_server(pack_dir: Path | str) -> FastMCP:
    """Create a FastMCP server from a knowledge pack directory.

    Args:
        pack_dir: Path to the knowledge pack root (containing docchat.yaml).

    Returns:
        Configured FastMCP instance ready to run.
    """
    pack_dir = Path(pack_dir)
    config = load_pack_config(pack_dir)

    # Load engine
    engine = KnowledgeEngine(pack_dir)
    engine.load()

    # Create MCP server
    mcp = FastMCP(
        name=config.assistant.name,
        instructions=(
            f"This MCP server provides documentation for {config.display_name}. "
            f"Use the tools below to find API feeds, route questions, "
            f"and retrieve detailed documentation."
        ),
    )

    # ------------------------------------------------------------------
    # Tool: list_feeds
    # ------------------------------------------------------------------

    @mcp.tool()
    def list_feeds() -> str:
        """List all available API feeds with their codes, names, and descriptions.

        Use this to get an overview of what feeds are available.
        Returns a JSON array of feed objects.
        """
        feeds = engine.list_feeds()
        return json.dumps(feeds, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Tool: search_by_field
    # ------------------------------------------------------------------

    @mcp.tool()
    def search_by_field(field_name: str) -> str:
        """Search for feeds that contain a specific field name.

        Args:
            field_name: The field name to search for (e.g. "userId", "email").

        Returns a JSON array of matching feeds.
        """
        # Look up field in engine's field index
        results = []
        seen: set[str] = set()
        for fname, code in engine._field_to_feed.items():
            if field_name.lower() in fname.lower() and code not in seen:
                seen.add(code)
                feed = engine._feeds.get(code)
                if feed:
                    results.append(feed)
        return json.dumps(results, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Tool: get_feed_info
    # ------------------------------------------------------------------

    @mcp.tool()
    def get_feed_info(feed_code: str) -> str:
        """Get detailed information and documentation for a specific feed.

        Args:
            feed_code: The feed code (e.g. "get-users", "MA1").

        Returns JSON with feed metadata and knowledge content (GUIDE + FAQ).
        """
        feed = engine._feeds.get(feed_code)
        if not feed:
            return json.dumps(
                {"error": f"Feed '{feed_code}' not found"},
                ensure_ascii=False,
            )

        knowledge = engine.get_feed_knowledge(
            feed_code, parts=["guide", "faq", "fields"]
        )
        result = {**feed, "knowledge": knowledge}
        return json.dumps(result, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Tool: route_question
    # ------------------------------------------------------------------

    @mcp.tool()
    def route_question(query: str) -> str:
        """Route a user's question to the most relevant feeds using deterministic matching.

        Uses trigger keywords, field names, and feed codes to find matches
        without any LLM call. Returns matched feeds, routing method, and
        knowledge text for the top matches.

        Args:
            query: The user's question in natural language.

        Returns JSON with matched_feeds, question_type, routing_method,
        and knowledge text.
        """
        result = engine.route(query)

        # Attach knowledge for matched feeds
        knowledge_parts = []
        for feed_tuple in result["matched_feeds"][:5]:  # Limit to top 5
            code = feed_tuple[0]
            parts = ["guide"]
            if result["question_type"] == "troubleshooting":
                parts = ["guide", "faq"]
            knowledge = engine.get_feed_knowledge(code, parts=parts)
            if knowledge:
                knowledge_parts.append(knowledge)

        # Add shared knowledge for general/troubleshooting
        if result["question_type"] in ("general", "troubleshooting"):
            shared = engine.get_shared_knowledge()
            if shared:
                knowledge_parts.append(shared)

        # Add overview for overview type
        if result["question_type"] == "overview":
            overview = engine.get_overview()
            if overview:
                knowledge_parts.append(overview)

        result["knowledge"] = "\n\n---\n\n".join(knowledge_parts)
        return json.dumps(result, ensure_ascii=False, default=str)

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    @mcp.resource(f"docchat://{config.name}/overview")
    def overview_resource() -> str:
        """API overview and coverage information."""
        return engine.get_overview() or "No overview available."

    @mcp.resource(f"docchat://{config.name}/shared")
    def shared_resource() -> str:
        """Shared knowledge (error codes, auth, FAQ)."""
        return engine.get_shared_knowledge() or "No shared knowledge available."

    @mcp.resource(f"docchat://{config.name}/feeds")
    def feeds_resource() -> str:
        """Compact routing summary of all feeds."""
        return engine.get_routing_summary() or "No feeds available."

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    @mcp.prompt()
    def api_expert_system() -> str:
        """System prompt for an API documentation expert."""
        from docchat.engine.prompts import build_system_prompt

        knowledge = engine.get_routing_summary()
        overview = engine.get_overview()
        full_knowledge = "\n\n".join(filter(None, [overview, knowledge]))
        return build_system_prompt(
            "usage",
            full_knowledge,
            lang="en",
            preamble=config.assistant.preamble_en,
        )

    @mcp.prompt()
    def troubleshooting_guide() -> str:
        """System prompt for troubleshooting API issues."""
        from docchat.engine.prompts import build_system_prompt

        shared = engine.get_shared_knowledge()
        overview = engine.get_overview()
        full_knowledge = "\n\n".join(filter(None, [overview, shared]))
        return build_system_prompt(
            "troubleshooting",
            full_knowledge,
            lang="en",
            preamble=config.assistant.preamble_en,
        )

    return mcp
