"""Tests for prompt template system."""

from docchat.engine.prompts import build_system_prompt, detect_language


def test_detect_language_zh():
    assert detect_language("NBA球员排名") == "zh"


def test_detect_language_en():
    assert detect_language("How to get users") == "en"


def test_detect_language_mixed():
    assert detect_language("MA2接口怎么用") == "zh"


def test_build_prompt_contains_knowledge():
    prompt = build_system_prompt("usage", "some knowledge", lang="en")
    assert "some knowledge" in prompt


def test_build_prompt_custom_preamble():
    prompt = build_system_prompt(
        "usage",
        "knowledge",
        lang="en",
        preamble="You are the Stripe API assistant.",
    )
    assert "Stripe" in prompt
    assert "Opta" not in prompt


def test_build_prompt_default_preamble():
    prompt = build_system_prompt("usage", "knowledge", lang="en")
    assert "API" in prompt
    assert "documentation" in prompt.lower()


def test_build_prompt_zh():
    prompt = build_system_prompt("usage", "知识内容", lang="zh")
    assert "知识内容" in prompt
    assert "中文" in prompt


def test_build_prompt_anti_hallucination():
    prompt = build_system_prompt("usage", "knowledge", lang="en")
    assert "fabricate" in prompt.lower() or "invent" in prompt.lower()


def test_build_prompt_overview_type():
    prompt = build_system_prompt("overview", "knowledge", lang="en")
    assert "category" in prompt.lower() or "total" in prompt.lower()
