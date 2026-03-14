# OpenAPI Import 功能设计

> docchat-mcp v0.2 核心功能：从 OpenAPI spec 自动生成知识包骨架

## 背景

当前用户使用 docchat-mcp 需要手动为每个 API endpoint 编写 META.yaml + GUIDE.md，这是最大的使用门槛。通过 `docchat import` 命令自动从 OpenAPI spec 生成 80% 的骨架文件，用户只需补充 triggers 关键词和使用注意事项。

## 命令设计

### 基本用法

```bash
docchat import petstore.json
```

一个位置参数（spec 文件路径），其他全部交互式确认。支持 JSON 和 YAML 格式的 OpenAPI spec（3.0/3.1，2.0 基本兼容）。

### 交互流程

```
$ docchat import petstore.json

📄 Parsed: petstore.json (OpenAPI 3.0.2)
   Found 12 endpoints across 4 resources

? How to group endpoints into feeds?
  > One feed per endpoint (12 feeds)
    One feed per resource (4 feeds)

? Target directory?
  > ./  (current directory)

? This directory already has a docchat pack with 3 feeds.
  Import into this pack? [Y/n]

Generating feeds...
  ✓ users/         — created
  ✓ posts/         — created
  ⚠ comments/      — already exists. Overwrite? [y/N]
  ✓ tags/          — created

✓ Generated 3 feeds, skipped 1.

Next steps:
  1. Add trigger keywords to each META.yaml
  2. Review and enrich GUIDE.md files
  3. Run `docchat validate` to check
```

### 非交互模式

```bash
docchat import petstore.json --yes --group endpoint
```

`--yes` 跳过所有确认，已存在的 feed 默认跳过（safe default）。`--group` 指定粒度（`endpoint` 或 `resource`），非交互模式下默认 `endpoint`。

### CLI 完整签名

```python
@main.command(name="import")
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--dir", "target_dir", default=".", help="Target knowledge pack directory")
@click.option("--group", type=click.Choice(["endpoint", "resource"]), help="Feed grouping granularity")
@click.option("--yes", is_flag=True, help="Non-interactive, skip existing feeds")
def import_cmd(spec_file, target_dir, group, yes): ...
```

- `--dir` 与 `init`/`build`/`validate` 保持一致
- 参数齐全时直接执行，缺参数时交互式补问

## OpenAPI 解析层

### 解析流程

1. 读取 JSON/YAML 文件
2. 检测版本（`openapi` 字段 → 3.x，`swagger` 字段 → 2.0）
3. 解析 `$ref` 引用（JSON Pointer 递归替换，手写实现）
4. 若为 2.0：将 `definitions` 映射到 `components/schemas`，`body` parameter 映射到 `requestBody`
5. 提取每个 path + method 的结构化数据

### 提取的数据

- `operationId` / 自动生成的 feed_code
- `summary` → feed_name
- `description` → description
- `parameters` → 参数表（name/type/required/description）
- `requestBody` → 请求体 schema
- `responses.200`（或 `2XX`/`201`/第一个 2xx） → response schema + examples
- `tags` → 用于按资源分组

### feed_code 生成规则

- 有 `operationId` → slugify（`listUsers` → `list-users`）
- 无 `operationId` → `{method}-{path-slug}`（`GET /api/users/{id}` → `get-api-users-id`）
- 资源粒度时 → 取 tag 名称（首选）；无 tag 时取 path 最后一个非参数段（`/api/users/{id}` → `users`，`/api/users/{id}/posts` → `user-posts` 以 `{parent}-{child}` 格式避免碰撞）

**目录名 = META.yaml 的 `name` 字段**，始终保持一致。

### OpenAPI 版本兼容

- **3.0/3.1**：完整支持（`components/schemas`、`requestBody`）
- **2.0 (Swagger)**：基本兼容。`basePath` + `paths` 拼接为完整路径写入 endpoint 字段。`definitions` 映射到 `components/schemas`。

### $ref 解析

手写 JSON Pointer 递归替换，不引入外部库。

- 处理 `#/components/schemas/User` 格式的本地引用
- 不支持外部文件引用（`$ref: "./other.yaml"`），遇到时跳过并警告
- **循环引用保护**：维护 visited set，检测到循环时停止展开，将该节点标记为 `{"type": "object", "description": "(circular ref)"}`
- **`allOf` 合并**：将 `allOf` 数组中的 schema 扁平合并 properties；`oneOf`/`anyOf` 取第一个 schema 作为代表

### 错误处理

- spec 文件不存在或格式错误 → 报错退出
- spec 中 `paths` 为空或不存在 → 报错：`"No API paths found in spec. Nothing to import."`
- 无法识别的 OpenAPI 版本 → 报错退出

## 文件生成层

### 目标目录规则

1. 检测 `target_dir` 下是否存在 `docchat.yaml`
2. **有 `docchat.yaml`**：读取配置，feeds 放入对应位置（零维度 → `feeds/`，有维度 → 按维度目录结构）
3. **无 `docchat.yaml`**：在 `target_dir` 下先运行 `init` 逻辑创建包骨架，再生成 feeds

### 两种粒度

**Endpoint 粒度**（一个 endpoint = 一个 feed）：

```
feeds/
├── list-users/
│   ├── META.yaml
│   └── GUIDE.md
├── get-user-by-id/
│   ├── META.yaml
│   └── GUIDE.md
└── create-user/
    ├── META.yaml
    └── GUIDE.md
```

**Resource 粒度**（按 tag 或 path 前缀分组）：

```
feeds/
├── users/
│   ├── META.yaml      # endpoint 字段为多行
│   └── GUIDE.md       # 按 ## GET /users、## GET /users/{id}、## POST /users 分 section
└── posts/
    ├── META.yaml
    └── GUIDE.md
```

资源粒度分组规则：
- 优先按 `tags` 分组（同 tag 的 endpoints 归为一个 feed）
- 无 tag 时按 path 前缀分组：取 path 最后一个非参数段，父子路径用 `{parent}-{child}` 避免碰撞
- 示例：`/users` + `/users/{id}` → `users`，`/users/{id}/posts` → `user-posts`

### META.yaml 模板

```yaml
name: list-users                   # 与目录名一致
feed_name: List Users
description: "Returns a paginated list of users"
endpoint: GET /api/users

triggers:
  keywords: []                     # 留空，用户/AI 后续补充
  scenarios: []

fields:                            # 从 response schema 提取顶层字段名
  - id
  - name
  - email
  - createdAt
```

### GUIDE.md 模板

````markdown
# List Users

Returns a paginated list of users.

## Endpoint

`GET /api/users`

## Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | integer | No | Page number |
| limit | integer | No | Items per page |

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| id | integer | User identifier |
| name | string | Full name |

## Example Request

> TODO: Add example request

## Example Response

```json
{
  "id": 1,
  "name": "string"
}
```

## Notes

> TODO: Add usage notes and tips
````

如果 spec 中有 `examples` 字段，直接填入 Example Request/Response；否则从 schema 生成类型骨架（`"string"`、`0`、`true`）。

**Response fields 提取规则**：提取顶层字段名。对于常见包装结构（`data`/`items`/`results` 等字段值为 array/object），额外展开一层提取内层字段。

### 冲突处理

- 交互模式：逐个确认 `Overwrite? [y/N]`
- 非交互模式（`--yes`）：跳过已存在的 feed

## 模块结构

### 新增文件

```
src/docchat/
├── importers/
│   ├── __init__.py
│   └── openapi.py
tests/
└── test_import_openapi.py
```

### 核心类

```python
# openapi.py

@dataclass
class EndpointInfo:
    method: str                     # GET, POST, ...
    path: str                       # /api/users/{id}
    operation_id: str | None
    summary: str
    description: str
    parameters: list[ParamInfo]
    request_body: dict | None       # 解析后的 schema
    response_schema: dict | None    # 200 response schema
    response_examples: dict | None  # examples
    tags: list[str]

@dataclass
class ParamInfo:
    name: str
    type: str
    required: bool
    description: str
    location: str                   # query, path, header

@dataclass
class FeedSkeleton:
    feed_code: str
    feed_name: str
    description: str
    endpoints: list[EndpointInfo]
    fields: list[str]               # 从 response schema 提取
    parameters: list[ParamInfo]     # 合并所有 endpoint 的参数
    examples: dict | None

@dataclass
class GenerateResult:
    created: list[str]
    skipped: list[str]
    overwritten: list[str]

class OpenAPIImporter:
    def __init__(self, spec_path: Path): ...
    def parse(self): ...
    def group_by_endpoint(self) -> list[FeedSkeleton]: ...
    def group_by_resource(self) -> list[FeedSkeleton]: ...
    def generate(self, feeds: list[FeedSkeleton], target_dir: Path,
                 on_conflict: Callable) -> GenerateResult: ...
```

### 不改动的部分

`KnowledgeEngine`、`mcp_server.py`、`prompts.py` 全部不动。Import 只负责生成文件，与引擎完全解耦。

## 依赖

### 新增运行时依赖

- **Rich** — 美化终端输出（Panel、彩色状态标记、Table），同时也将用于美化现有 CLI 命令（`init`/`validate`/`build` 等）的输出
- **questionary** — 交互式选择和确认提示（arrow-key 选择菜单体验优于 `click.prompt`）

两个库都是轻量级的，Rich 是 Python CLI 生态事实标准，questionary 仅依赖 prompt_toolkit。

### 不引入的

- 无 OpenAPI 解析库（`$ref` 手写解析）
- 无 LLM 依赖

## 测试计划

`tests/test_import_openapi.py`，使用内联 dict fixture（与 `conftest.py` 风格一致）：

- 解析 JSON 格式的 spec
- 解析 YAML 格式的 spec
- `$ref` 引用解析（含循环引用保护）
- `allOf` 合并
- Endpoint 粒度分组
- Resource 粒度分组（按 tag / 按 path 前缀 / 碰撞避免）
- feed_code 生成（有/无 operationId）
- 目录名与 META.yaml `name` 一致性
- META.yaml 生成内容验证
- GUIDE.md 生成内容验证（有/无 examples）
- Response fields 嵌套展开（包装结构）
- 冲突跳过
- 冲突覆盖
- OpenAPI 2.0 兼容（basePath 拼接）
- 空 paths 错误处理
