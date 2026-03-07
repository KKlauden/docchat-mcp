# DocChat MCP

> 将 API 文档转化为智能 MCP 服务器——确定性路由 + 分层知识注入。

[![PyPI version](https://img.shields.io/pypi/v/docchat-mcp)](https://pypi.org/project/docchat-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | 中文

**DocChat** 将你的 API 文档转化为智能 [MCP](https://modelcontextprotocol.io/) 服务器。Claude Code 等 AI 编程助手可以用自然语言查询你的 API 文档——**约 80% 的查询通过确定性路由解决**（零 LLM 调用）。

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

```bash
docchat init --name my-api
```

这会生成目录结构。然后编写文档——每个 API 端点对应一个 feed 目录：

```bash
my-api/
└── feeds/
    └── get-users/
        ├── META.yaml   # 触发关键词 + 字段名（用于路由）
        └── GUIDE.md    # 使用指南（用于回答）
```

格式参见 [docs/writing-guide.md](docs/writing-guide.md)，也可以使用 `docchat-author` skill 让 Claude Code 辅助编写。

### 3. 验证和构建

```bash
docchat validate    # 检查格式
docchat build       # 验证索引加载
```

### 4. 连接 Claude Code

```bash
# 注册为本地 MCP 服务器（通过 stdio 在本机运行）
claude mcp add my-api -- docchat mcp --dir ./my-api-docs/

# 或通过 uvx（无需预先安装）
claude mcp add my-api -- uvx docchat-mcp mcp --dir ./my-api-docs/
```

完成。现在你在 Claude Code 中询问 API 相关问题时，它会通过本地 MCP 服务器查询 DocChat，检索相关文档，生成准确回答。

### 团队共享（可选）

如果需要多人使用同一份知识包：

```bash
# 在共享服务器上启动 HTTP 模式
docchat serve --port 8000

# 团队成员远程连接
claude mcp add my-api --transport http http://your-server:8000/mcp/
```

## 特性

- **确定性路由** — 触发关键词、字段名、feed code 匹配查询，无需 LLM
- **分层知识注入** — feed 级、概览、共享知识、话题级关键词匹配
- **自定义维度** — 按任意层级组织 feed（产品、版本、地区等）
- **MCP 原生** — 4 个 Tool、3 个 Resource、2 个 Prompt，兼容任何 MCP 客户端
- **零 LLM 依赖** — 引擎只提供数据，AI 推理由客户端完成
- **CLI 工具链** — `init` / `build` / `validate` / `serve` / `mcp`

## 知识包结构

```
my-api/
├── docchat.yaml          # 包配置（名称、维度、助手设定）
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
