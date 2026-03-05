"""Prompt templates for the DocChat system.

Provides build_system_prompt() to assemble system prompts from modular
components. Two complete prompt sets (zh / en) are maintained. The preamble
is parameterized — knowledge packs provide their own via docchat.yaml.
"""

import re

# ── Language detection ──

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def detect_language(text: str) -> str:
    """Return 'zh' if *text* contains CJK characters, else 'en'."""
    return "zh" if _CJK_RE.search(text) else "en"


# ═══════════════════════════════════════════════════════════
#  Chinese prompt set
# ═══════════════════════════════════════════════════════════

_TYPE_INSTRUCTIONS_ZH: dict[str, str] = {
    "overview": """回复结构：
1. 第一行给出准确的接口总数
2. 按功能分类列出接口，每个类别用 `### 类别名（N 个）` 作为标题
3. 每个类别只列出 2-3 个代表性接口（`feed_code` 名称 — 一句话用途）
4. 不要列出所有接口的完整清单
5. 末尾用 blockquote 引导用户按类别名称追问，查看完整列表

注意：overview 回答不使用两段式结构，直接输出分类摘要。""",
    "usage": """回复结构 — 严格遵循两段式输出：

直达区（分割线之前，≤100 字）：
- 一句话说明该接口是什么、解决什么问题
- 给出接口路径

---

### 详细说明
- 参数的必填/可选状态严格忠于文档原文，不得将条件必填简化为必填
- 如果存在多种参数组合方式（如 A+B 或 C+B），必须全部列出
- 如果需要先调用其他接口获取 ID/UUID，用 `### 调用依赖` 小节展示箭头链
- 参数表使用 `### 参数说明` 小节
- 给出一个示例请求 URL，使用 `### 示例请求` 小节""",
    "troubleshooting": """回复结构 — 严格遵循两段式输出：

直达区（分割线之前，≤100 字）：
- 一句话指出最可能的原因

---

### 排查步骤
- 编号列表，从最可能的原因开始
- 优先检查 FAQ 中的已知问题""",
    "general": """回复结构 — 严格遵循两段式输出：

直达区（分割线之前，≤100 字）：
- 一句话直接回答核心问题

---

### 详细说明
- 基于参考资料展开说明
- 如涉及具体参数，给出精确的值和限制""",
}

_DEFAULT_PREAMBLE_ZH = "你是 API 技术支持助手。请基于以下文档信息回答用户的问题。"

_RESPONSE_REQUIREMENTS_ZH = """回答要求：
- 用简洁的中文回答
- 严格遵循上述回复结构，直达区和详细区之间用 `---` 分隔
- 直达区 ≤100 字，直接命中用户核心问题
- 详细区 ≤800 字，除非用户要求详细说明
- 不要重复用户已经知道的基本信息
- 不要引用文档原文，用自己的语言总结要点
- **严禁虚构接口代码**：仅引用上方文档中实际出现的接口代码，绝不猜测或编造不存在的代码"""

_FORMAT_RULES_ZH = """格式规范（严格遵守 Markdown 语法）：
- 章节标题必须使用 `###` 三级标题语法，禁止用加粗文本代替标题
- 接口路径、字段名、参数名、接口代码在任何位置都必须用反引号包裹
- URL 必须用 Markdown 链接格式
- 使用有序列表（1. 2. 3.）表示步骤，无序列表（- ）表示要点
- 禁止使用 `#` 或 `##`（一二级标题），仅使用 `###` 和 `####`"""


# ═══════════════════════════════════════════════════════════
#  English prompt set
# ═══════════════════════════════════════════════════════════

_TYPE_INSTRUCTIONS_EN: dict[str, str] = {
    "overview": """Response structure:
1. First line: state the exact total number of feeds
2. Group feeds by function category, each with a `### Category Name (N feeds)` heading
3. List only 2-3 representative feeds per category (`feed_code` name — one-line purpose)
4. Do NOT list every feed exhaustively
5. End with a blockquote inviting the user to ask about a specific category for the full list

Note: overview answers skip the two-section format; output the categorized summary directly.""",
    "usage": """Response structure — strictly follow the two-section format:

Quick answer (before the divider, ≤100 words):
- One sentence: what this feed is and what problem it solves
- Provide the endpoint path

---

### Details
- Parameter required/optional status must strictly follow the source docs
- If multiple parameter combinations exist, list them all
- If a prerequisite call is needed, add a `### Call Dependencies` subsection
- Use a `### Parameters` subsection for the parameter table
- Provide one example request URL in a `### Example Request` subsection""",
    "troubleshooting": """Response structure — strictly follow the two-section format:

Quick answer (before the divider, ≤100 words):
- One sentence identifying the most likely cause

---

### Troubleshooting Steps
- Numbered list, starting from the most likely cause
- Prioritize known issues from the FAQ""",
    "general": """Response structure — strictly follow the two-section format:

Quick answer (before the divider, ≤100 words):
- One sentence directly answering the core question

---

### Details
- Expand based on the reference materials
- If specific parameters are involved, provide exact values and constraints""",
}

_DEFAULT_PREAMBLE_EN = (
    "You are an API technical support assistant. "
    "Answer the user's questions based on the documentation provided below."
)

_RESPONSE_REQUIREMENTS_EN = """Response requirements:
- Reply in concise English
- Strictly follow the response structure above; separate the quick-answer and detail sections with `---`
- Quick answer ≤100 words, directly addressing the user's core question
- Detail section ≤800 words, unless the user explicitly asks for more
- Do not repeat basic information the user already knows
- Do not quote the documentation verbatim; summarize key points in your own words
- **Never fabricate feed codes**: only reference codes that actually appear in the documentation above. Never guess or invent codes that do not exist"""

_FORMAT_RULES_EN = """Formatting rules (strict Markdown syntax):
- Section headings must use `###` level-3 syntax; never substitute bold text for headings
- Endpoint paths, field names, parameter names, and feed codes must always be wrapped in backticks
- URLs must use Markdown link format: `[description](https://...)`
- Use ordered lists (1. 2. 3.) for steps, unordered lists (- ) for bullet points
- Never use `#` or `##` (level 1-2 headings); only use `###` and `####`"""


# ═══════════════════════════════════════════════════════════
#  Language-indexed lookup
# ═══════════════════════════════════════════════════════════

_PROMPTS = {
    "zh": {
        "type_instructions": _TYPE_INSTRUCTIONS_ZH,
        "default_preamble": _DEFAULT_PREAMBLE_ZH,
        "requirements": _RESPONSE_REQUIREMENTS_ZH,
        "format_rules": _FORMAT_RULES_ZH,
    },
    "en": {
        "type_instructions": _TYPE_INSTRUCTIONS_EN,
        "default_preamble": _DEFAULT_PREAMBLE_EN,
        "requirements": _RESPONSE_REQUIREMENTS_EN,
        "format_rules": _FORMAT_RULES_EN,
    },
}


def build_system_prompt(
    question_type: str,
    knowledge_block: str,
    lang: str = "zh",
    preamble: str | None = None,
) -> str:
    """Assemble the full system prompt from modular components.

    Args:
        question_type: One of "overview", "usage", "troubleshooting", "general".
        knowledge_block: Pre-assembled knowledge text.
        lang: "zh" or "en" — selects the matching prompt template set.
        preamble: Custom preamble from docchat.yaml. If None, uses default.

    Returns:
        Complete system prompt string ready for the LLM.
    """
    p = _PROMPTS.get(lang, _PROMPTS["en"])
    instruction = p["type_instructions"].get(
        question_type, p["type_instructions"]["usage"]
    )
    actual_preamble = preamble or p["default_preamble"]

    return (
        f"{actual_preamble}\n\n"
        f"{instruction}\n\n"
        f"{p['requirements']}\n\n"
        f"{p['format_rules']}\n\n"
        f"---\n\n"
        f"{knowledge_block}"
    )
