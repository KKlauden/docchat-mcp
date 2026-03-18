# Skill 体系增强计划

**背景：** 分析 Agent Skill 五大设计模式（Tool Wrapper / Generator / Reviewer / Inversion / Pipeline）后，发现 docchat-mcp 现有的 `docchat-author` skill 已天然融合 Inversion + Generator + Pipeline 三种模式，但缺少 **内容质量审查（Reviewer）**。此外 MCP 消费端（AI 助手）对 tools 的使用引导不够充分。

**Goal:** 新增 `docchat-reviewer` skill，增强 `api_expert_system` MCP Prompt，更新文档。

**决策记录：**

| 讨论项 | 决策 | 理由 |
|--------|------|------|
| reviewer 纯 Skill 还是 CLI？ | 纯 Skill | reviewer 的核心价值在 AI 判断（关键词质量、描述准确性），确定性检查已有 validate 覆盖 |
| consumer 独立 skill 还是增强 Prompt？ | 增强 `api_expert_system` Prompt | MCP Prompt 对所有客户端生效，比 .claude/skills/ 更普适 |
| references/ 抽离共享？ | 不抽离，保持内联 | 仅 2 个消费者，抽离需改 init/import 模板逻辑，过度工程 |
| reviewer 自动修复？ | 第一版只报告 | 职责清晰，输出末尾引导用户调用 docchat-author 修复 |

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `skills/docchat-reviewer.md` | 新建 | 知识包内容质量审查 skill |
| `src/docchat/data/docchat-reviewer.md` | 新建 | 打包版（docchat init/import 生成给用户） |
| `src/docchat/mcp_server.py` | 修改 | 增强 `api_expert_system` Prompt |
| `src/docchat/importers/openapi.py` | 修改 | init/import 时生成 reviewer skill 文件 |
| `README.md` / `README.zh-CN.md` | 修改 | Features 增加 reviewer 说明 |

---

## Chunk 1: docchat-reviewer skill

> Reviewer 模式——将检查标准内联为 checklist，AI 逐条审查并按严重度分组输出。

### Task 1: 创建 docchat-reviewer skill

**Files:**
- Create: `skills/docchat-reviewer.md`
- Create: `src/docchat/data/docchat-reviewer.md`（内容相同）

- [ ] **Step 1: 编写 skill 文件**

核心设计：

**触发条件：** 用户要求 "review"、"audit"、"check quality"、"评审" 知识包

**执行流程：**
1. 运行 `docchat validate` 先做结构校验，确保基础结构无误
2. 扫描知识包所有 feeds 的 META.yaml / GUIDE.md / FAQ.md / fields/
3. 逐条应用内联 checklist（见下方）
4. 按严重度分组输出（Error → Warning → Info）
5. 给出总分（1-10）和 Top 3 改进建议
6. 输出末尾引导："如需修复以上问题，可使用 /docchat-author 并将本报告作为输入。"

**内联 checklist：**

| 维度 | Error（必须修） | Warning（建议修） | Info（可选优化） |
|------|-----------------|-------------------|-----------------|
| **Triggers** | META.yaml 缺少 triggers.keywords | 只有单语言关键词 | 同义词少于 3 组 |
| **关键词质量** | 包含过于泛化的单词（"data", "API", "get"） | 缺少动作+资源组合变体 | 缺少领域特定术语 |
| **Fields** | META.yaml 无 fields 列表 | fields 与 Example Response 的 JSON key 不一致 | 缺少 fields/ 拆分文件 |
| **GUIDE.md** | 文件不存在 | 缺少 Parameters 或 Example Response | 缺少 Notes 章节 |
| **FAQ.md** | — | 存在但不遵循 Check/Cause/Resolution | 不存在（复杂 feed 建议补） |
| **Shared** | INDEX.yaml 引用了不存在的文件 | 缺 error_codes.md | 缺 auth 文档 |
| **Overview** | INDEX.md 不存在 | feed 列表与实际 feeds/ 不一致 | 缺 Base URL 或 Auth |

与 `docchat validate` 的分工：
- `validate` = 结构校验（文件是否存在、YAML 是否合法）→ CLI 命令，确定性
- `reviewer` = 内容审查（关键词质量、文档完整性、一致性）→ AI skill，需要判断力

---

### Task 2: 将 reviewer 集成到 init/import 流程

**Files:**
- Modify: `src/docchat/importers/openapi.py`（或 init 相关逻辑）

- [ ] **Step 1: init/import 生成 reviewer skill 文件到 `.claude/skills/docchat-reviewer.md`**

与 docchat-author 相同的分发机制：从 `src/docchat/data/docchat-reviewer.md` 复制到用户知识包。

---

## Chunk 2: 增强 api_expert_system Prompt

### Task 3: 优化 MCP Prompt

**File:** `src/docchat/mcp_server.py`

- [ ] **Step 1: 增强 `api_expert_system` Prompt，补充 tool 使用最佳实践**

新增规则：
1. 优先用 `route_question` — 一次调用拿到路由结果 + 分层知识 + system prompt
2. 仅在需要浏览完整列表时用 `list_feeds`
3. 拿到 feed code 后如需细节，用 `get_feed_info` 获取完整文档再回答
4. 字段级问题用 `search_by_field` 精确匹配
5. 查不到结果时引导用户换关键词，不要编造

---

## Chunk 3: 文档更新

### Task 4: 更新 README

- [ ] **Step 1: 英文 README Features 增加 reviewer 说明**
- [ ] **Step 2: 中文 README 同步更新**

---

## 最终 Skill 矩阵

| Skill | 模式 | 用途 | 用户 |
|-------|------|------|------|
| `docchat-author` | Inversion + Generator + Pipeline | 创建/改进知识包 | 知识包作者 |
| `docchat-reviewer` | Reviewer | 审查知识包内容质量 | 知识包作者 |

MCP 消费端引导通过增强 `api_expert_system` Prompt 实现（非独立 skill）。

---

## 注意事项

- Skill 文件使用英文编写（面向国际用户），triggers.keywords 示例保留中文展示多语言支持
- reviewer 的关键词质量检查标准内联在 skill 中，不抽离到 references/
- reviewer 第一版只做报告，不自动修复
