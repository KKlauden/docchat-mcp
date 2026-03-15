# DocChat MCP

> 将 API 文档转化为智能 MCP 服务器——确定性路由 + 分层知识注入。

[![PyPI version](https://img.shields.io/pypi/v/docchat-mcp)](https://pypi.org/project/docchat-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | 中文

**DocChat** 将你的 API 文档转化为智能 [MCP](https://modelcontextprotocol.io/) 服务器。Claude Code 可以用自然语言查询你的 API 文档——**约 80% 的查询通过确定性路由解决**（零 LLM 调用）。

> **说明：** DocChat 当前主要针对 **Claude Code** 优化，其他 AI 编码工具的支持后续跟进。

## 使用场景

你在开发一个需要调用第三方 API 的应用。你希望 Claude Code 能理解那个 API——参数、响应字段、错误码、最佳实践——从而写出正确的集成代码。

```
你的 API 文档 → DocChat → MCP 服务器（本地运行）→ Claude Code 编码时随时查询
```

DocChat 是桥梁：它把文档转化为结构化知识，让 AI 助手可以按需搜索和检索。

## 工作原理

```
                          你的电脑
┌───────────────────────────────────────────────────┐
│                                                   │
│  Claude Code ◄── stdio ──► docchat mcp            │
│    (LLM)                    (本地进程)              │
│      │                         │                  │
│      │ "users 接口              │ 读取             │
│      │  怎么调用？"              ▼                  │
│      │                    ./my-api-docs/           │
│      │                    ├── META.yaml            │
│      │                    ├── GUIDE.md             │
│      ▼                    └── ...                  │
│  基于检索到的文档                                    │
│  生成回答                                          │
│                                                   │
└───────────────────────────────────────────────────┘
```

引擎负责**路由 + 知识检索**，AI 客户端负责**推理**。无需外部服务，无需额外 LLM 调用。

## 快速开始

### 1. 安装

```bash
pip install docchat-mcp
```

### 2. 创建知识包

**方式 A：从 OpenAPI spec 导入**（推荐）

```bash
docchat import your-api-spec.json
```

自动解析 OpenAPI spec（JSON/YAML，v2.0/3.x），生成 feed 骨架和 `AUTHORING.md` 编写指南。然后让 AI 助手补充完善：

```
# 在 Claude Code 中（skill 已自动安装为 /docchat-author）
> 帮我完善文档

# 在其他 AI 工具中
> 阅读 AUTHORING.md，帮我完善知识包文档
```

**方式 B：让 AI 全程生成**

如果你有文档 URL 或只是 API 的描述，可以跳过 `import`，直接告诉 AI：

```
> 我需要为 Petstore API 创建 docchat 知识包。
  文档地址：https://petstore.swagger.io
  请阅读 AUTHORING.md 了解格式规范。
```

**方式 C：从零开始（手动）**

```bash
docchat init --name my-api
```

然后手动创建每个 feed 目录。格式参见 [docs/writing-guide.md](docs/writing-guide.md)。

### 3. 验证和构建

```bash
docchat validate    # 检查格式
docchat build       # 验证索引加载
```

### 4. 连接 Claude Code

```bash
# 在知识包目录下：
docchat connect

# 或从其他目录：
docchat connect --dir /path/to/my-api-docs/
```

完成。现在你在 Claude Code 中询问 API 相关问题时，它会通过本地 MCP 服务器查询 DocChat，检索相关文档，生成准确回答。

<details>
<summary>手动注册（不使用 <code>docchat connect</code>）</summary>

```bash
claude mcp add my-api -- docchat mcp --dir ./my-api-docs/

# 或通过 uvx（无需预先安装）
claude mcp add my-api -- uvx --from docchat-mcp docchat mcp --dir ./my-api-docs/
```
</details>

### 团队共享（可选）

如果需要多人使用同一份知识包：

```bash
# 在共享服务器上启动 HTTP 模式
docchat serve --port 8710

# 团队成员远程连接
claude mcp add my-api --transport http http://your-server:8710/mcp/
```

## 特性

- **确定性路由** — 触发关键词、字段名、feed code 匹配查询，无需 LLM
- **分层知识注入** — feed 级、概览、共享知识、话题级关键词匹配
- **AI 辅助编写** — 内置 `docchat-author` skill，引导 AI 从任意来源（spec 文件、URL、描述）生成完整知识包
- **自定义维度** — 按任意层级组织 feed（产品、版本、地区等）
- **MCP 原生** — 4 个 Tool、3 个 Resource、2 个 Prompt，兼容任何 MCP 客户端
- **零 LLM 依赖** — 引擎只提供数据，AI 推理由客户端完成
- **OpenAPI 导入** — `docchat import spec.json` 从 OpenAPI spec 自动生成 feed 骨架（v2.0/3.x）
- **CLI 工具链** — `init` / `import` / `build` / `validate` / `serve` / `mcp`

## 知识包结构

```
my-api/
├── docchat.yaml          # 包配置（名称、维度、助手设定）
├── AUTHORING.md          # AI 编写指南（工具无关）
├── .claude/skills/       # Claude Code 自动发现此 skill
│   └── docchat-author.md
├── _shared/              # 共享知识（错误码、认证等）
│   ├── INDEX.yaml        # 话题关键词映射
│   └── error_codes.md
├── _overview/            # API 概览
│   └── INDEX.md
└── feeds/                # 每个 API 端点一个目录
    ├── get-users/
    │   ├── META.yaml     # 触发条件、字段、描述
    │   ├── GUIDE.md      # 使用指南
    │   ├── FAQ.md        # 可选：常见问题排查
    │   └── fields/       # 可选：字段参考
    └── get-posts/
        ├── META.yaml
        └── GUIDE.md
```

完整规范参见 [docs/knowledge-pack-format.md](docs/knowledge-pack-format.md)。

## 自定义维度

通过 `docchat.yaml` 按任意层级组织 feed：

```yaml
# 简单 API（所有 feed 平铺）
dimensions: []

# 两个维度（产品 × 运动）
dimensions:
  - key: product
    values: { rest: "REST API", ws: "WebSocket" }
  - key: sport
    values: { soccer: "Soccer", basketball: "Basketball" }
```

## MCP Tool

| Tool | 说明 |
|------|------|
| `list_feeds` | 列出所有可用 feed |
| `search_by_field` | 按字段名搜索 feed |
| `get_feed_info` | 获取 feed 详情 + 文档内容 |
| `route_question` | 路由查询并返回匹配的 feed + 知识文本 |

## 更新方式

**知识文件更新**（META.yaml、GUIDE.md 等）：重启 Claude Code 即可，MCP 服务器启动时会重新加载。

**引擎版本更新**（新版 docchat-mcp）：

```bash
pip install --upgrade docchat-mcp
# 然后重启 Claude Code

# 如果使用 uvx，先清除缓存：
uv cache clean docchat-mcp
```

## 为什么不用 RAG？

| 方案 | 局限 | DocChat |
|------|------|---------|
| Swagger UI | 只能浏览，无法问答 | 自然语言查询 |
| ChatGPT + 文档 | 全量灌入，上下文溢出 | 分层精准注入 |
| RAG（向量检索） | 嵌入质量不稳定，路由不可控 | 确定性路由（~80% 零 LLM） |
| 无 MCP | AI 无法访问文档 | MCP 原生，Claude Code 直连 |

## 演示

在线体验：[docchat.site](https://docchat.site)

## 许可证

MIT
