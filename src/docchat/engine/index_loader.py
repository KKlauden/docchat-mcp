"""KnowledgeEngine — load knowledge packs and route queries deterministically.

Core responsibilities:
1. Scan knowledge pack directories, build trigger/field/topic indexes
2. Deterministic routing: overview → trigger → field → explicit code
3. Knowledge retrieval: feed-level, shared, overview
"""

import re
from pathlib import Path

import yaml

from docchat.schema import PackConfig, load_pack_config

# ------------------------------------------------------------------
# Overview intent patterns
# ------------------------------------------------------------------

_OVERVIEW_PATTERNS = [
    "都有哪些接口", "有哪些接口", "有什么接口", "接口列表",
    "api列表", "所有接口", "全部接口", "接口概览", "api概览",
    "能做什么", "能查什么", "支持哪些", "支持什么",
    "哪些feed", "哪些 feed", "list all feeds", "what feeds",
    "available feeds", "available apis", "all feeds", "feed list",
    "list all endpoints", "what endpoints", "available endpoints",
]

# ------------------------------------------------------------------
# Question type patterns
# ------------------------------------------------------------------

_TROUBLESHOOTING_PATTERNS = [
    "为空", "为0", "不对", "不正确", "报错", "错误", "异常",
    "返回为空", "没有数据", "数据不对", "empty", "error", "wrong",
    "missing", "null", "404", "403", "500", "timeout",
    "不返回", "查不到", "not working", "broken",
]

_GENERAL_PATTERNS = [
    "认证", "authentication", "auth", "oauth",
    "错误码", "error code", "分页", "pagination",
    "格式", "format",
]

_MIN_TRIGGER_SUBSTR_LEN = 3


class KnowledgeEngine:
    """Load a knowledge pack and provide deterministic routing + knowledge retrieval."""

    def __init__(self, pack_dir: Path | str):
        self.pack_dir = Path(pack_dir)
        self.config: PackConfig | None = None

        # feed_code → feed metadata dict
        self._feeds: dict[str, dict] = {}
        # feed_code → Path to feed directory
        self._feed_dirs: dict[str, Path] = {}

        # keyword (lowercased) → [feed_code, ...]
        self._trigger_to_feed: dict[str, list[str]] = {}
        # field_name → feed_code
        self._field_to_feed: dict[str, str] = {}

        # Shared topics: topic_path → keywords
        self._topic_keywords: dict[str, list[str]] = {}
        self._topic_products: dict[str, str | None] = {}

        # Overview and shared dirs
        self._shared_dir: Path | None = None
        self._overview_dir: Path | None = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self):
        """Scan the knowledge pack and build all indexes."""
        self.config = load_pack_config(self.pack_dir)

        # Discover feed directories
        self._discover_feeds()

        # Build indexes from META.yaml files
        self._build_trigger_index()
        self._build_field_index()

        # Load shared topic index
        self._load_shared_index()

        # Discover overview directory
        self._discover_overview()

    def _discover_feeds(self):
        """Scan for feed directories based on dimension count."""
        self._feeds = {}
        self._feed_dirs = {}

        if not self.config or not self.config.dimensions:
            # Zero dimensions: feeds are in pack_dir/feeds/
            feeds_dir = self.pack_dir / "feeds"
            if feeds_dir.is_dir():
                self._scan_feed_dir(feeds_dir)
        else:
            # Multi-dimension: scan dimension value combinations
            self._scan_dimension_dirs(self.pack_dir, 0)

    def _scan_dimension_dirs(self, base: Path, dim_idx: int):
        """Recursively scan dimension directories."""
        if not self.config:
            return
        if dim_idx >= len(self.config.dimensions):
            # At leaf level — look for feed directories here
            if base.is_dir():
                self._scan_feed_dir(base)
            return
        dim = self.config.dimensions[dim_idx]
        for value_key in dim.values:
            child = base / value_key
            if child.is_dir():
                self._scan_dimension_dirs(child, dim_idx + 1)

    def _scan_feed_dir(self, feeds_dir: Path):
        """Scan a directory for feed subdirectories containing META.yaml."""
        for child in feeds_dir.iterdir():
            if not child.is_dir():
                continue
            if child.name.startswith("_"):
                continue
            meta_path = child / "META.yaml"
            if meta_path.exists():
                meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
                feed_code = meta.get("name", child.name)
                self._feeds[feed_code] = {
                    "feed_code": feed_code,
                    "feed_name": meta.get("feed_name", feed_code),
                    "description": meta.get("description", ""),
                    "endpoint": meta.get("endpoint", ""),
                }
                self._feed_dirs[feed_code] = child

    def _build_trigger_index(self):
        """Build keyword → [feed_code] mapping from META.yaml triggers."""
        self._trigger_to_feed = {}
        for feed_code, feed_dir in self._feed_dirs.items():
            meta_path = feed_dir / "META.yaml"
            if not meta_path.exists():
                continue
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            triggers = meta.get("triggers", {})
            for kw_line in triggers.get("keywords", []):
                # Split by Chinese comma (、) and English comma (,)
                parts = str(kw_line).replace("\u3001", ",").split(",")
                for part in parts:
                    keyword = part.strip().lower()
                    if not keyword:
                        continue
                    self._trigger_to_feed.setdefault(keyword, []).append(feed_code)

    def _build_field_index(self):
        """Build field_name → feed_code mapping from META.yaml fields."""
        self._field_to_feed = {}
        for feed_code, feed_dir in self._feed_dirs.items():
            meta_path = feed_dir / "META.yaml"
            if not meta_path.exists():
                continue
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            for field in meta.get("fields", []):
                if isinstance(field, str):
                    self._field_to_feed[field] = feed_code

    def _load_shared_index(self):
        """Load _shared/INDEX.yaml for topic keyword matching."""
        self._topic_keywords = {}
        self._topic_products = {}
        self._shared_dir = self.pack_dir / "_shared"
        if not self._shared_dir.is_dir():
            self._shared_dir = None
            return

        index_path = self._shared_dir / "INDEX.yaml"
        if not index_path.exists():
            return

        shared_index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        for topic in shared_index.get("topics", []):
            path = topic["path"]
            self._topic_keywords[path] = topic.get("keywords", [])
            self._topic_products[path] = topic.get("product")

    def _discover_overview(self):
        """Find _overview directory."""
        overview = self.pack_dir / "_overview"
        self._overview_dir = overview if overview.is_dir() else None

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def list_feeds(self, **dim_values) -> list[dict]:
        """List all feeds (optionally filtered by dimension values)."""
        # For now, return all feeds (dimension filtering is for multi-dim packs)
        return list(self._feeds.values())

    def route(self, message: str, **dim_values) -> dict:
        """Deterministic routing pipeline: overview → trigger → field → explicit code.

        Returns:
            {
                "matched_feeds": [(feed_code, feed_name, description), ...],
                "question_type": str,
                "routing_method": str,
                "needs_llm_fallback": bool,
            }
        """
        # 1. Overview detection
        if self._detect_overview(message):
            all_feeds = [
                (f["feed_code"], f["feed_name"], f["description"])
                for f in self._feeds.values()
            ]
            return {
                "matched_feeds": all_feeds,
                "question_type": "overview",
                "routing_method": "deterministic:overview",
                "needs_llm_fallback": False,
            }

        # 2. Trigger keywords
        trigger_matches = self._detect_triggers(message)
        # 3. Field names
        field_matches = self._detect_fields(message)
        # 4. Explicit feed codes
        explicit_matches = self._detect_explicit_codes(message)

        # Merge and deduplicate
        seen: set[str] = set()
        matched: list[tuple[str, str, str]] = []
        method = ""

        def _add(code: str):
            if code not in seen and code in self._feeds:
                seen.add(code)
                f = self._feeds[code]
                matched.append((f["feed_code"], f["feed_name"], f["description"]))

        if trigger_matches:
            for code in trigger_matches:
                _add(code)
            method = "deterministic:trigger"
        if field_matches:
            for code in field_matches:
                _add(code)
            method = method or "deterministic:field"
        if explicit_matches:
            for code in explicit_matches:
                _add(code)
            method = method or "deterministic:feed_code"

        if matched:
            qtype = self._infer_question_type(message, has_matched=True)
            return {
                "matched_feeds": matched,
                "question_type": qtype,
                "routing_method": method,
                "needs_llm_fallback": False,
            }

        # No deterministic match
        return {
            "matched_feeds": [],
            "question_type": self._infer_question_type(message, has_matched=False),
            "routing_method": "none",
            "needs_llm_fallback": True,
        }

    # ------------------------------------------------------------------
    # Knowledge retrieval
    # ------------------------------------------------------------------

    def get_feed_knowledge(
        self, feed_code: str, parts: list[str] | None = None, **dim_values
    ) -> str:
        """Load feed-level knowledge files.

        Args:
            feed_code: Feed identifier.
            parts: Which files to load: "meta", "guide", "faq", "fields".
                   Defaults to ["guide"].
        """
        if parts is None:
            parts = ["guide"]

        feed_dir = self._feed_dirs.get(feed_code)
        if not feed_dir:
            return ""

        file_map = {
            "meta": "META.yaml",
            "guide": "GUIDE.md",
            "faq": "FAQ.md",
        }

        content_parts = []
        for part in parts:
            if part == "fields":
                fields_dir = feed_dir / "fields"
                if fields_dir.is_dir():
                    for field_file in sorted(fields_dir.glob("*.md")):
                        content_parts.append(
                            field_file.read_text(encoding="utf-8")
                        )
                continue
            filename = file_map.get(part)
            if not filename:
                continue
            path = feed_dir / filename
            if path.exists():
                content_parts.append(path.read_text(encoding="utf-8"))

        return "\n\n---\n\n".join(content_parts)

    def get_shared_knowledge(self, **dim_values) -> str:
        """Load shared knowledge files (error codes, FAQ, etc.)."""
        if not self._shared_dir:
            return ""

        content_parts = []
        # Load all .md files directly in _shared/ (not in subdirs)
        for md_file in sorted(self._shared_dir.glob("*.md")):
            content_parts.append(md_file.read_text(encoding="utf-8"))

        return "\n\n---\n\n".join(content_parts)

    def get_shared_topic(self, keyword: str, **dim_values) -> str:
        """Load a shared topic file matching the given keyword."""
        if not self._shared_dir:
            return ""

        keyword_lower = keyword.lower()
        for topic_path, keywords in self._topic_keywords.items():
            for kw in keywords:
                if kw.lower() == keyword_lower or keyword_lower in kw.lower():
                    full_path = self._shared_dir / topic_path
                    if full_path.exists():
                        return full_path.read_text(encoding="utf-8")
        return ""

    def get_overview(self, **dim_values) -> str:
        """Load overview knowledge (_overview/ directory)."""
        if not self._overview_dir:
            return ""

        content_parts = []
        for filename in ["INDEX.md", "COVERAGE_TIERS.md"]:
            path = self._overview_dir / filename
            if path.exists():
                content_parts.append(path.read_text(encoding="utf-8"))

        return "\n\n---\n\n".join(content_parts)

    def get_routing_summary(self) -> str:
        """Build a compact routing summary of all feeds."""
        lines = []
        for feed in self._feeds.values():
            desc = feed["description"].strip()
            first_sentence = desc.split(". ")[0].rstrip(".")
            if len(first_sentence) > 120:
                first_sentence = first_sentence[:117] + "..."
            lines.append(
                f"[{feed['feed_code']}] {feed['feed_name']} — {first_sentence}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal detection methods
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_overview(message: str) -> bool:
        msg_lower = message.lower()
        return any(p in msg_lower for p in _OVERVIEW_PATTERNS)

    def _detect_triggers(self, message: str) -> list[str]:
        """Match trigger keywords against the message."""
        message_lower = message.lower()
        matched: list[str] = []
        seen: set[str] = set()

        for keyword, feed_codes in self._trigger_to_feed.items():
            is_short_ascii = (
                len(keyword) < _MIN_TRIGGER_SUBSTR_LEN and keyword.isascii()
            )
            if is_short_ascii:
                if not re.search(
                    r"\b" + re.escape(keyword) + r"\b",
                    message_lower,
                    re.IGNORECASE,
                ):
                    continue
            else:
                if keyword not in message_lower:
                    continue

            for code in feed_codes:
                if code not in seen:
                    seen.add(code)
                    matched.append(code)

        return matched

    def _detect_fields(self, message: str) -> list[str]:
        """Match field names against the message."""
        matched: list[str] = []
        seen: set[str] = set()
        for field_name, code in self._field_to_feed.items():
            if field_name in message and code not in seen:
                seen.add(code)
                matched.append(code)
        return matched

    def _detect_explicit_codes(self, message: str) -> list[str]:
        """Detect feed codes explicitly mentioned in the message."""
        mentioned = []
        msg_lower = message.lower()
        for code in self._feeds:
            if code.lower() in msg_lower:
                mentioned.append(code)
        return mentioned

    @staticmethod
    def _infer_question_type(message: str, has_matched: bool) -> str:
        """Infer question type from message content."""
        msg_lower = message.lower()

        if any(p in msg_lower for p in _TROUBLESHOOTING_PATTERNS):
            return "troubleshooting"

        if not has_matched:
            if any(p in msg_lower for p in _GENERAL_PATTERNS):
                return "general"

        return "usage"
