"""Tests for KnowledgeEngine — index loading, routing, knowledge retrieval."""

import pytest
from docchat.engine.index_loader import KnowledgeEngine


def test_load_pack(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    codes = [f["feed_code"] for f in engine.list_feeds()]
    assert "get-users" in codes
    assert "get-posts" in codes


def test_trigger_routing(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    result = engine.route("How to get user list")
    codes = [f[0] for f in result["matched_feeds"]]
    assert "get-users" in codes


def test_trigger_routing_chinese(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    result = engine.route("获取用户列表")
    codes = [f[0] for f in result["matched_feeds"]]
    assert "get-users" in codes


def test_field_routing(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    result = engine.route("What is the userId field")
    codes = [f[0] for f in result["matched_feeds"]]
    assert "get-users" in codes


def test_explicit_code_routing(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    result = engine.route("Tell me about get-users")
    codes = [f[0] for f in result["matched_feeds"]]
    assert "get-users" in codes


def test_overview_routing(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    result = engine.route("有哪些接口")
    assert result["routing_method"] == "deterministic:overview"
    assert len(result["matched_feeds"]) >= 2


def test_no_match_needs_llm(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    result = engine.route("unrelated random question xyz")
    assert result["needs_llm_fallback"] is True
    assert result["matched_feeds"] == []


def test_get_feed_knowledge_guide(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    knowledge = engine.get_feed_knowledge("get-users", parts=["guide"])
    assert "GET /api/users" in knowledge


def test_get_feed_knowledge_faq(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    knowledge = engine.get_feed_knowledge("get-users", parts=["faq"])
    assert "empty" in knowledge.lower()


def test_get_shared_knowledge(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    shared = engine.get_shared_knowledge()
    assert "Error Codes" in shared


def test_get_shared_topic_by_keyword(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    topic = engine.get_shared_topic("authentication")
    assert "OAuth" in topic


def test_get_overview(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    overview = engine.get_overview()
    assert "API Overview" in overview


def test_question_type_inference(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    # Troubleshooting pattern
    result = engine.route("userId 为空怎么办")
    assert result["question_type"] == "troubleshooting"


def test_list_feeds_returns_metadata(minimal_pack):
    engine = KnowledgeEngine(minimal_pack)
    engine.load()
    feeds = engine.list_feeds()
    users_feed = next(f for f in feeds if f["feed_code"] == "get-users")
    assert users_feed["feed_name"] == "Get Users"
    assert "users" in users_feed["description"].lower()
