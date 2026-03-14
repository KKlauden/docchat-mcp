# OpenAPI Import 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `docchat import` 命令，从 OpenAPI spec 自动生成知识包 feed 骨架文件。

**Architecture:** 新增 `src/docchat/importers/openapi.py` 模块，包含 OpenAPI 解析器（含 $ref 解析）和文件生成器。CLI 层使用 questionary 做交互式选择，Rich 美化输出。与 KnowledgeEngine 完全解耦。

**Tech Stack:** Python dataclasses, PyYAML（已有），Rich（新增），questionary（新增）

**Spec:** `docs/specs/2026-03-14-openapi-import-design.md`

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/docchat/importers/__init__.py` | 包初始化 |
| `src/docchat/importers/openapi.py` | OpenAPI 解析 + feed 骨架生成（~300 行） |
| `src/docchat/cli.py` | 新增 `import` 子命令（~80 行新增） |
| `pyproject.toml` | 新增 rich + questionary 依赖 |
| `tests/test_import_openapi.py` | 导入功能测试（~20 个用例） |

---

## Chunk 1: 依赖 + OpenAPI 解析器核心

### Task 1: 新增依赖

**Files:**
- Modify: `pyproject.toml:8-12`

- [ ] **Step 1: 添加 rich 和 questionary 到 dependencies**

```toml
dependencies = [
    "fastmcp>=3.0.2",
    "pyyaml>=6.0",
    "click>=8.0",
    "rich>=13.0",
    "questionary>=2.0",
]
```

- [ ] **Step 2: 安装依赖验证**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv sync`
Expected: 成功安装 rich 和 questionary

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: 添加 rich 和 questionary 依赖"
```

---

### Task 2: $ref 解析器 + OpenAPI 解析器数据结构

**Files:**
- Create: `src/docchat/importers/__init__.py`
- Create: `src/docchat/importers/openapi.py`
- Create: `tests/test_import_openapi.py`

- [ ] **Step 1: 写 $ref 解析的测试**

```python
# tests/test_import_openapi.py
"""Tests for OpenAPI importer."""

import json
import pytest
from pathlib import Path
from docchat.importers.openapi import OpenAPIImporter


# -- Fixtures --

MINIMAL_SPEC_3 = {
    "openapi": "3.0.2",
    "info": {"title": "Pet Store", "version": "1.0.0"},
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "description": "Returns all pets from the system.",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "description": "Max number of pets to return",
                        "schema": {"type": "integer"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "A list of pets",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Pet"},
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "operationId": "createPet",
                "summary": "Create a pet",
                "description": "Creates a new pet in the store.",
                "tags": ["pets"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Pet"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Pet created",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Pet"}
                            }
                        },
                    }
                },
            },
        },
        "/pets/{petId}": {
            "get": {
                "operationId": "getPetById",
                "summary": "Get a pet by ID",
                "description": "Returns a single pet.",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "description": "The pet ID",
                        "schema": {"type": "integer"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "A pet",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Pet"}
                            }
                        },
                    }
                },
            },
        },
        "/owners": {
            "get": {
                "operationId": "listOwners",
                "summary": "List owners",
                "description": "Returns all pet owners.",
                "tags": ["owners"],
                "responses": {
                    "200": {
                        "description": "A list of owners",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Owner"},
                                }
                            }
                        },
                    }
                },
            }
        },
    },
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "tag": {"type": "string"},
                    "owner": {"$ref": "#/components/schemas/Owner"},
                },
            },
            "Owner": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
            },
        }
    },
}


CIRCULAR_REF_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Circular", "version": "1.0.0"},
    "paths": {
        "/categories": {
            "get": {
                "operationId": "listCategories",
                "summary": "List categories",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Category"}
                            }
                        },
                    }
                },
            }
        }
    },
    "components": {
        "schemas": {
            "Category": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "children": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Category"},
                    },
                },
            }
        }
    },
}


SWAGGER_2_SPEC = {
    "swagger": "2.0",
    "info": {"title": "Legacy API", "version": "1.0.0"},
    "basePath": "/api/v1",
    "paths": {
        "/users": {
            "get": {
                "operationId": "getUsers",
                "summary": "Get users",
                "description": "Returns users list.",
                "parameters": [
                    {
                        "name": "page",
                        "in": "query",
                        "type": "integer",
                        "required": False,
                        "description": "Page number",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "schema": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/User"},
                        },
                    }
                },
            }
        }
    },
    "definitions": {
        "User": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
        }
    },
}


ALLOF_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "AllOf Test", "version": "1.0.0"},
    "paths": {
        "/items": {
            "get": {
                "operationId": "listItems",
                "summary": "List items",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "allOf": [
                                        {"$ref": "#/components/schemas/Base"},
                                        {"$ref": "#/components/schemas/Extra"},
                                    ]
                                }
                            }
                        },
                    }
                },
            }
        }
    },
    "components": {
        "schemas": {
            "Base": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
            "Extra": {
                "type": "object",
                "properties": {
                    "color": {"type": "string"},
                },
            },
        }
    },
}


EMPTY_PATHS_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Empty", "version": "1.0.0"},
    "paths": {},
}


WRAPPER_RESPONSE_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Wrapper", "version": "1.0.0"},
    "paths": {
        "/items": {
            "get": {
                "operationId": "listItems",
                "summary": "List items",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "data": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "integer"},
                                                    "title": {"type": "string"},
                                                },
                                            },
                                        },
                                        "meta": {
                                            "type": "object",
                                            "properties": {
                                                "total": {"type": "integer"},
                                            },
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            }
        }
    },
}


EXAMPLE_IN_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Example", "version": "1.0.0"},
    "paths": {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "List users",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                    },
                                },
                                "example": {
                                    "id": 1,
                                    "name": "Alice",
                                },
                            }
                        },
                    }
                },
            }
        }
    },
}


NO_OPERATION_ID_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "NoOpId", "version": "1.0.0"},
    "paths": {
        "/api/users/{id}": {
            "get": {
                "summary": "Get user by ID",
                "responses": {"200": {"description": "OK"}},
            }
        }
    },
}


@pytest.fixture
def spec_file(tmp_path):
    """Write a spec dict to a temp JSON file and return its path."""
    def _write(spec_dict, filename="spec.json"):
        path = tmp_path / filename
        path.write_text(json.dumps(spec_dict), encoding="utf-8")
        return path
    return _write


# -- $ref resolution tests --

def test_ref_resolution(spec_file):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    # Pet schema should be resolved
    endpoints = importer.group_by_endpoint()
    pet_list = [e for e in endpoints if e.feed_code == "list-pets"]
    assert len(pet_list) == 1
    # Should have fields from resolved Pet schema
    assert "id" in pet_list[0].fields
    assert "name" in pet_list[0].fields


def test_circular_ref_no_crash(spec_file):
    path = spec_file(CIRCULAR_REF_SPEC)
    importer = OpenAPIImporter(path)
    importer.parse()
    endpoints = importer.group_by_endpoint()
    assert len(endpoints) == 1
    # Should have id and name but not crash on circular children
    assert "id" in endpoints[0].fields
    assert "name" in endpoints[0].fields


def test_allof_merge(spec_file):
    path = spec_file(ALLOF_SPEC)
    importer = OpenAPIImporter(path)
    importer.parse()
    endpoints = importer.group_by_endpoint()
    assert len(endpoints) == 1
    # Should have fields from both Base and Extra
    assert "id" in endpoints[0].fields
    assert "name" in endpoints[0].fields
    assert "color" in endpoints[0].fields
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv run pytest tests/test_import_openapi.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'docchat.importers'`

- [ ] **Step 3: 实现 $ref 解析 + 数据结构 + parse()**

```python
# src/docchat/importers/__init__.py
"""OpenAPI and other format importers."""
```

```python
# src/docchat/importers/openapi.py
"""Import feeds from OpenAPI specifications."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ParamInfo:
    """A single API parameter."""

    name: str
    type: str
    required: bool
    description: str
    location: str  # query, path, header, cookie


@dataclass
class EndpointInfo:
    """Parsed data for a single API endpoint."""

    method: str
    path: str
    operation_id: str | None
    summary: str
    description: str
    parameters: list[ParamInfo]
    request_body: dict | None
    response_schema: dict | None
    response_examples: dict | None
    tags: list[str]


@dataclass
class FeedSkeleton:
    """Generated feed structure ready for file output."""

    feed_code: str
    feed_name: str
    description: str
    endpoints: list[EndpointInfo]
    fields: list[str]
    parameters: list[ParamInfo]
    examples: dict | None


@dataclass
class GenerateResult:
    """Summary of file generation results."""

    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    overwritten: list[str] = field(default_factory=list)


def _slugify(text: str) -> str:
    """Convert camelCase/PascalCase/snake_case to kebab-case slug."""
    # Insert hyphens before uppercase letters (camelCase → camel-Case)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", text)
    # Replace non-alphanumeric with hyphens
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s)
    return s.strip("-").lower()


def _resolve_refs(obj, root: dict, visited: set | None = None) -> dict | list | str | int | float | bool | None:
    """Recursively resolve $ref pointers in an OpenAPI spec.

    Args:
        obj: Current node in the spec tree.
        root: The full spec (for resolving JSON Pointer paths).
        visited: Set of $ref paths already being resolved (circular guard).
    """
    if visited is None:
        visited = set()

    if isinstance(obj, dict):
        if "$ref" in obj:
            ref_path = obj["$ref"]
            if not ref_path.startswith("#/"):
                # External ref — skip
                return {"type": "object", "description": f"(external ref: {ref_path})"}
            if ref_path in visited:
                # Circular ref — stop
                return {"type": "object", "description": "(circular ref)"}
            visited = visited | {ref_path}
            # Resolve JSON Pointer: #/components/schemas/Pet → ["components", "schemas", "Pet"]
            parts = ref_path[2:].split("/")
            target = root
            for part in parts:
                target = target.get(part, {}) if isinstance(target, dict) else {}
            return _resolve_refs(target, root, visited)

        # Handle allOf: merge properties
        if "allOf" in obj:
            merged: dict = {}
            merged_props: dict = {}
            for sub in obj["allOf"]:
                resolved = _resolve_refs(sub, root, visited)
                if isinstance(resolved, dict):
                    merged_props.update(resolved.get("properties", {}))
                    for k, v in resolved.items():
                        if k != "properties":
                            merged.setdefault(k, v)
            if merged_props:
                merged["properties"] = merged_props
            return merged

        # Handle oneOf/anyOf: take first schema
        for key in ("oneOf", "anyOf"):
            if key in obj and obj[key]:
                return _resolve_refs(obj[key][0], root, visited)

        return {k: _resolve_refs(v, root, visited) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_resolve_refs(item, root, visited) for item in obj]

    return obj


def _extract_fields(schema: dict | None) -> list[str]:
    """Extract field names from a resolved response schema.

    For wrapper structures (data/items/results containing array/object),
    expand one level deeper.
    """
    if not schema or not isinstance(schema, dict):
        return []

    # If array with items, use items schema
    if schema.get("type") == "array" and "items" in schema:
        return _extract_fields(schema["items"])

    props = schema.get("properties", {})
    if not props:
        return []

    fields = []
    wrapper_keys = {"data", "items", "results", "records", "rows", "list"}
    for name, prop in props.items():
        if name in wrapper_keys and isinstance(prop, dict):
            inner_type = prop.get("type")
            if inner_type == "array" and "items" in prop:
                inner_fields = _extract_fields(prop["items"])
                if inner_fields:
                    fields.extend(inner_fields)
                    continue
            elif inner_type == "object" and "properties" in prop:
                inner_fields = list(prop["properties"].keys())
                if inner_fields:
                    fields.extend(inner_fields)
                    continue
        fields.append(name)
    return fields


def _generate_example(schema: dict | None) -> dict | list | str | int | bool | None:
    """Generate a skeleton example value from a schema."""
    if not schema or not isinstance(schema, dict):
        return None
    t = schema.get("type", "object")
    if t == "string":
        return "string"
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "boolean":
        return True
    if t == "array":
        item = _generate_example(schema.get("items", {}))
        return [item] if item is not None else []
    if t == "object" or "properties" in schema:
        props = schema.get("properties", {})
        return {k: _generate_example(v) for k, v in props.items()}
    return None


class OpenAPIImporter:
    """Parse an OpenAPI spec and generate feed skeleton files."""

    def __init__(self, spec_path: Path | str):
        self.spec_path = Path(spec_path)
        self._raw: dict = {}
        self._spec: dict = {}  # After $ref resolution
        self._version: str = ""
        self._base_path: str = ""
        self._endpoints: list[EndpointInfo] = []

    def parse(self):
        """Read and parse the spec file."""
        text = self.spec_path.read_text(encoding="utf-8")
        suffix = self.spec_path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            self._raw = yaml.safe_load(text)
        else:
            self._raw = json.loads(text)

        if not self._raw.get("paths"):
            raise ValueError("No API paths found in spec. Nothing to import.")

        # Detect version
        if "openapi" in self._raw:
            self._version = self._raw["openapi"]
        elif "swagger" in self._raw:
            self._version = self._raw["swagger"]
            self._base_path = self._raw.get("basePath", "")
            # Normalize Swagger 2.0 to 3.x structure
            self._normalize_swagger2()
        else:
            raise ValueError("Cannot detect OpenAPI version. Expected 'openapi' or 'swagger' field.")

        # Resolve $ref
        self._spec = _resolve_refs(self._raw, self._raw)

        # Extract endpoints
        self._endpoints = self._extract_endpoints()

    def _normalize_swagger2(self):
        """Map Swagger 2.0 structures to OpenAPI 3.x equivalents in-place."""
        # definitions → components.schemas
        if "definitions" in self._raw:
            self._raw.setdefault("components", {})["schemas"] = self._raw.pop("definitions")

        # Normalize responses with inline schema
        for path_item in (self._raw.get("paths") or {}).values():
            for method_obj in path_item.values():
                if not isinstance(method_obj, dict):
                    continue
                for status, resp in (method_obj.get("responses") or {}).items():
                    if isinstance(resp, dict) and "schema" in resp and "content" not in resp:
                        schema = resp.pop("schema")
                        resp["content"] = {
                            "application/json": {"schema": schema}
                        }

    def _extract_endpoints(self) -> list[EndpointInfo]:
        """Extract EndpointInfo from all paths."""
        endpoints = []
        http_methods = {"get", "post", "put", "patch", "delete", "head", "options"}

        for path, path_item in (self._spec.get("paths") or {}).items():
            if not isinstance(path_item, dict):
                continue
            # Path-level parameters
            path_params = path_item.get("parameters", [])

            for method, op in path_item.items():
                if method.lower() not in http_methods or not isinstance(op, dict):
                    continue

                # Merge path-level + operation-level parameters
                all_params = path_params + op.get("parameters", [])
                params = []
                for p in all_params:
                    if not isinstance(p, dict):
                        continue
                    p_schema = p.get("schema", {})
                    params.append(ParamInfo(
                        name=p.get("name", ""),
                        type=p_schema.get("type", p.get("type", "string")),
                        required=p.get("required", False),
                        description=p.get("description", ""),
                        location=p.get("in", "query"),
                    ))

                # Response schema + examples
                resp_schema = None
                resp_examples = None
                responses = op.get("responses", {})
                # Find first 2xx response
                for status in ["200", "201", "202", "2XX"]:
                    if status in responses:
                        resp = responses[status]
                        content = resp.get("content", {})
                        json_content = content.get("application/json", {})
                        resp_schema = json_content.get("schema")
                        resp_examples = json_content.get("example")
                        break

                # Request body
                request_body = None
                rb = op.get("requestBody", {})
                if isinstance(rb, dict):
                    rb_content = rb.get("content", {})
                    rb_json = rb_content.get("application/json", {})
                    request_body = rb_json.get("schema")

                full_path = self._base_path + path if self._base_path else path

                endpoints.append(EndpointInfo(
                    method=method.upper(),
                    path=full_path,
                    operation_id=op.get("operationId"),
                    summary=op.get("summary", ""),
                    description=op.get("description", ""),
                    parameters=params,
                    request_body=request_body,
                    response_schema=resp_schema,
                    response_examples=resp_examples,
                    tags=op.get("tags", []),
                ))

        return endpoints

    @property
    def endpoint_count(self) -> int:
        return len(self._endpoints)

    @property
    def resource_count(self) -> int:
        return len(self._group_by_tag_or_path().keys())

    def group_by_endpoint(self) -> list[FeedSkeleton]:
        """One feed per endpoint."""
        skeletons = []
        for ep in self._endpoints:
            code = _slugify(ep.operation_id) if ep.operation_id else self._path_to_code(ep.method, ep.path)
            fields = _extract_fields(ep.response_schema)
            examples = ep.response_examples
            if not examples and ep.response_schema:
                examples = _generate_example(ep.response_schema)

            skeletons.append(FeedSkeleton(
                feed_code=code,
                feed_name=ep.summary or code,
                description=ep.description or ep.summary or "",
                endpoints=[ep],
                fields=fields,
                parameters=ep.parameters,
                examples=examples,
            ))
        return skeletons

    def group_by_resource(self) -> list[FeedSkeleton]:
        """One feed per resource (grouped by tag or path prefix)."""
        groups = self._group_by_tag_or_path()
        skeletons = []
        for group_name, endpoints in groups.items():
            code = _slugify(group_name)
            # Merge fields, params, examples from all endpoints
            all_fields: list[str] = []
            all_params: list[ParamInfo] = []
            seen_fields: set[str] = set()
            seen_params: set[str] = set()

            for ep in endpoints:
                for f in _extract_fields(ep.response_schema):
                    if f not in seen_fields:
                        seen_fields.add(f)
                        all_fields.append(f)
                for p in ep.parameters:
                    if p.name not in seen_params:
                        seen_params.add(p.name)
                        all_params.append(p)

            first_ep = endpoints[0]
            description = first_ep.description or first_ep.summary or ""

            skeletons.append(FeedSkeleton(
                feed_code=code,
                feed_name=group_name.replace("-", " ").title(),
                description=description,
                endpoints=endpoints,
                fields=all_fields,
                parameters=all_params,
                examples=None,
            ))
        return skeletons

    def _group_by_tag_or_path(self) -> dict[str, list[EndpointInfo]]:
        """Group endpoints by tag (preferred) or path prefix."""
        groups: dict[str, list[EndpointInfo]] = {}

        # Check if any endpoints have tags
        has_tags = any(ep.tags for ep in self._endpoints)

        if has_tags:
            for ep in self._endpoints:
                tag = ep.tags[0] if ep.tags else "default"
                groups.setdefault(tag, []).append(ep)
        else:
            for ep in self._endpoints:
                key = self._path_to_resource_key(ep.path)
                groups.setdefault(key, []).append(ep)

        return groups

    @staticmethod
    def _path_to_code(method: str, path: str) -> str:
        """Generate feed code from method + path when no operationId."""
        slug = path.strip("/").replace("/", "-").replace("{", "").replace("}", "")
        return f"{method.lower()}-{slug}" if slug else method.lower()

    @staticmethod
    def _path_to_resource_key(path: str) -> str:
        """Extract resource key from path for grouping.

        /api/users → users
        /api/users/{id} → users
        /api/users/{id}/posts → user-posts (parent-child to avoid collision)
        """
        parts = [p for p in path.strip("/").split("/") if not p.startswith("{")]
        if not parts:
            return "root"
        if len(parts) == 1:
            return parts[-1]
        # Use last non-param segment; if there are multiple, use parent-child
        # to avoid collision
        return f"{parts[-2]}-{parts[-1]}" if len(parts) >= 2 else parts[-1]
```

- [ ] **Step 4: 运行测试**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv run pytest tests/test_import_openapi.py::test_ref_resolution tests/test_import_openapi.py::test_circular_ref_no_crash tests/test_import_openapi.py::test_allof_merge -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/docchat/importers/ tests/test_import_openapi.py
git commit -m "feat: OpenAPI 解析器核心 — $ref 解析、数据结构、parse()"
```

---

### Task 3: 解析功能完整测试

**Files:**
- Modify: `tests/test_import_openapi.py`

- [ ] **Step 1: 添加解析相关的完整测试**

```python
# 追加到 tests/test_import_openapi.py

def test_parse_yaml_format(tmp_path):
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.dump(MINIMAL_SPEC_3, allow_unicode=True), encoding="utf-8")
    importer = OpenAPIImporter(path)
    importer.parse()
    assert importer.endpoint_count == 4


def test_parse_empty_paths(spec_file):
    path = spec_file(EMPTY_PATHS_SPEC)
    importer = OpenAPIImporter(path)
    with pytest.raises(ValueError, match="No API paths"):
        importer.parse()


def test_swagger2_compat(spec_file):
    path = spec_file(SWAGGER_2_SPEC)
    importer = OpenAPIImporter(path)
    importer.parse()
    endpoints = importer.group_by_endpoint()
    assert len(endpoints) == 1
    # basePath should be prepended
    assert endpoints[0].endpoints[0].path == "/api/v1/users"
    assert "id" in endpoints[0].fields
    assert "name" in endpoints[0].fields


def test_feed_code_with_operation_id(spec_file):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    codes = [f.feed_code for f in importer.group_by_endpoint()]
    assert "list-pets" in codes
    assert "create-pet" in codes
    assert "get-pet-by-id" in codes


def test_feed_code_without_operation_id(spec_file):
    path = spec_file(NO_OPERATION_ID_SPEC)
    importer = OpenAPIImporter(path)
    importer.parse()
    endpoints = importer.group_by_endpoint()
    assert len(endpoints) == 1
    assert endpoints[0].feed_code == "get-api-users-id"


def test_wrapper_response_fields(spec_file):
    path = spec_file(WRAPPER_RESPONSE_SPEC)
    importer = OpenAPIImporter(path)
    importer.parse()
    endpoints = importer.group_by_endpoint()
    # Should unwrap 'data' and get inner fields
    assert "id" in endpoints[0].fields
    assert "title" in endpoints[0].fields


def test_example_from_spec(spec_file):
    path = spec_file(EXAMPLE_IN_SPEC)
    importer = OpenAPIImporter(path)
    importer.parse()
    endpoints = importer.group_by_endpoint()
    assert endpoints[0].examples == {"id": 1, "name": "Alice"}
```

- [ ] **Step 2: 运行全部测试**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv run pytest tests/test_import_openapi.py -v`
Expected: 全部 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_import_openapi.py
git commit -m "test: OpenAPI 解析完整测试 — YAML/Swagger2/wrapper/example"
```

---

## Chunk 2: 分组逻辑 + 文件生成

### Task 4: 分组逻辑测试

**Files:**
- Modify: `tests/test_import_openapi.py`

- [ ] **Step 1: 添加分组测试**

```python
# 追加到 tests/test_import_openapi.py

def test_group_by_endpoint_count(spec_file):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_endpoint()
    assert len(feeds) == 4  # listPets, createPet, getPetById, listOwners


def test_group_by_resource_with_tags(spec_file):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_resource()
    codes = [f.feed_code for f in feeds]
    assert len(feeds) == 2  # pets, owners
    assert "pets" in codes
    assert "owners" in codes


def test_group_by_resource_merges_fields(spec_file):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_resource()
    pets = [f for f in feeds if f.feed_code == "pets"][0]
    # Should have merged fields from all pet endpoints
    assert "id" in pets.fields
    assert "name" in pets.fields


def test_resource_grouping_no_tags(spec_file):
    """Without tags, group by path prefix."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "NoTags", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {"summary": "List users", "responses": {"200": {"description": "OK"}}},
            },
            "/users/{id}": {
                "get": {"summary": "Get user", "responses": {"200": {"description": "OK"}}},
            },
            "/posts": {
                "get": {"summary": "List posts", "responses": {"200": {"description": "OK"}}},
            },
        },
    }
    path = spec_file(spec)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_resource()
    codes = [f.feed_code for f in feeds]
    assert "users" in codes
    assert "posts" in codes
    assert len(feeds) == 2  # /users and /users/{id} merged
```

- [ ] **Step 2: 运行测试**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv run pytest tests/test_import_openapi.py -v -k "group"
Expected: 全部 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_import_openapi.py
git commit -m "test: 分组逻辑测试 — endpoint/resource/tag/path"
```

---

### Task 5: 文件生成器

**Files:**
- Modify: `src/docchat/importers/openapi.py`
- Modify: `tests/test_import_openapi.py`

- [ ] **Step 1: 写文件生成测试**

```python
# 追加到 tests/test_import_openapi.py

import yaml as yaml_lib  # 避免与 fixture 冲突（如果有）
from docchat.importers.openapi import OpenAPIImporter


def test_generate_creates_feed_dirs(spec_file, tmp_path):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_endpoint()

    target = tmp_path / "output"
    target.mkdir()

    result = importer.generate(feeds, target, on_conflict=lambda code: "skip")
    assert len(result.created) == 4
    for code in ["list-pets", "create-pet", "get-pet-by-id", "list-owners"]:
        feed_dir = target / code
        assert feed_dir.is_dir()
        assert (feed_dir / "META.yaml").exists()
        assert (feed_dir / "GUIDE.md").exists()


def test_generate_meta_content(spec_file, tmp_path):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_endpoint()

    target = tmp_path / "output"
    target.mkdir()
    importer.generate(feeds, target, on_conflict=lambda code: "skip")

    meta = yaml_lib.safe_load((target / "list-pets" / "META.yaml").read_text())
    assert meta["name"] == "list-pets"
    assert meta["feed_name"] == "List all pets"
    assert meta["endpoint"] == "GET /pets"
    assert meta["triggers"]["keywords"] == []
    assert "id" in meta["fields"]


def test_generate_guide_content(spec_file, tmp_path):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_endpoint()

    target = tmp_path / "output"
    target.mkdir()
    importer.generate(feeds, target, on_conflict=lambda code: "skip")

    guide = (target / "list-pets" / "GUIDE.md").read_text()
    assert "# List all pets" in guide
    assert "## Parameters" in guide
    assert "limit" in guide
    assert "## Response Fields" in guide


def test_generate_with_example(spec_file, tmp_path):
    path = spec_file(EXAMPLE_IN_SPEC)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_endpoint()

    target = tmp_path / "output"
    target.mkdir()
    importer.generate(feeds, target, on_conflict=lambda code: "skip")

    guide = (target / "list-users" / "GUIDE.md").read_text()
    assert '"Alice"' in guide


def test_generate_skip_existing(spec_file, tmp_path):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_endpoint()

    target = tmp_path / "output"
    target.mkdir()
    # Pre-create one feed dir
    (target / "list-pets").mkdir()
    (target / "list-pets" / "META.yaml").write_text("existing: true\n")

    result = importer.generate(feeds, target, on_conflict=lambda code: "skip")
    assert "list-pets" in result.skipped
    # Original file should be untouched
    assert "existing: true" in (target / "list-pets" / "META.yaml").read_text()


def test_generate_overwrite_existing(spec_file, tmp_path):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_endpoint()

    target = tmp_path / "output"
    target.mkdir()
    (target / "list-pets").mkdir()
    (target / "list-pets" / "META.yaml").write_text("existing: true\n")

    result = importer.generate(feeds, target, on_conflict=lambda code: "overwrite")
    assert "list-pets" in result.overwritten
    meta = yaml_lib.safe_load((target / "list-pets" / "META.yaml").read_text())
    assert meta["name"] == "list-pets"


def test_generate_resource_guide_multi_endpoint(spec_file, tmp_path):
    path = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(path)
    importer.parse()
    feeds = importer.group_by_resource()

    target = tmp_path / "output"
    target.mkdir()
    importer.generate(feeds, target, on_conflict=lambda code: "skip")

    guide = (target / "pets" / "GUIDE.md").read_text()
    # Should have sections for each method
    assert "## GET /pets" in guide
    assert "## POST /pets" in guide
    assert "## GET /pets/{petId}" in guide
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv run pytest tests/test_import_openapi.py -v -k "generate"`
Expected: FAIL — `AttributeError: 'OpenAPIImporter' object has no attribute 'generate'`

- [ ] **Step 3: 实现 generate() 方法**

在 `OpenAPIImporter` 类中追加：

```python
    def generate(
        self,
        feeds: list[FeedSkeleton],
        target_dir: Path,
        on_conflict: callable,
    ) -> GenerateResult:
        """Generate META.yaml + GUIDE.md for each feed.

        Args:
            feeds: List of FeedSkeleton to generate.
            target_dir: Directory to create feed subdirectories in.
            on_conflict: Callback(feed_code) → "skip" | "overwrite".
        """
        result = GenerateResult()

        for feed in feeds:
            feed_dir = target_dir / feed.feed_code
            if feed_dir.exists():
                action = on_conflict(feed.feed_code)
                if action == "skip":
                    result.skipped.append(feed.feed_code)
                    continue
                result.overwritten.append(feed.feed_code)
            else:
                feed_dir.mkdir(parents=True)
                result.created.append(feed.feed_code)

            # Write META.yaml
            meta = {
                "name": feed.feed_code,
                "feed_name": feed.feed_name,
                "description": feed.description,
                "endpoint": self._format_endpoints(feed.endpoints),
                "triggers": {"keywords": [], "scenarios": []},
                "fields": feed.fields,
            }
            (feed_dir / "META.yaml").write_text(
                yaml.dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )

            # Write GUIDE.md
            guide = self._render_guide(feed)
            (feed_dir / "GUIDE.md").write_text(guide, encoding="utf-8")

        return result

    @staticmethod
    def _format_endpoints(endpoints: list[EndpointInfo]) -> str:
        """Format endpoint(s) for META.yaml."""
        if len(endpoints) == 1:
            ep = endpoints[0]
            return f"{ep.method} {ep.path}"
        return "\n".join(f"{ep.method} {ep.path}" for ep in endpoints)

    def _render_guide(self, feed: FeedSkeleton) -> str:
        """Render GUIDE.md content for a feed."""
        lines: list[str] = []

        if len(feed.endpoints) == 1:
            self._render_single_endpoint_guide(lines, feed)
        else:
            self._render_multi_endpoint_guide(lines, feed)

        return "\n".join(lines) + "\n"

    def _render_single_endpoint_guide(self, lines: list[str], feed: FeedSkeleton):
        ep = feed.endpoints[0]
        lines.append(f"# {feed.feed_name}")
        lines.append("")
        if feed.description:
            lines.append(feed.description)
            lines.append("")

        lines.append("## Endpoint")
        lines.append("")
        lines.append(f"`{ep.method} {ep.path}`")
        lines.append("")

        self._render_params(lines, ep.parameters)
        self._render_response_fields(lines, feed.fields)
        self._render_examples(lines, feed.examples)
        self._render_notes(lines)

    def _render_multi_endpoint_guide(self, lines: list[str], feed: FeedSkeleton):
        lines.append(f"# {feed.feed_name}")
        lines.append("")
        if feed.description:
            lines.append(feed.description)
            lines.append("")

        for ep in feed.endpoints:
            lines.append(f"## {ep.method} {ep.path}")
            lines.append("")
            if ep.summary:
                lines.append(ep.summary)
                lines.append("")
            if ep.description and ep.description != ep.summary:
                lines.append(ep.description)
                lines.append("")

            self._render_params(lines, ep.parameters)

            ep_fields = _extract_fields(ep.response_schema)
            self._render_response_fields(lines, ep_fields)

            examples = ep.response_examples
            if not examples and ep.response_schema:
                examples = _generate_example(ep.response_schema)
            self._render_examples(lines, examples)

        self._render_notes(lines)

    @staticmethod
    def _render_params(lines: list[str], params: list[ParamInfo]):
        if not params:
            return
        lines.append("## Parameters")
        lines.append("")
        lines.append("| Name | Type | Required | Description |")
        lines.append("|------|------|----------|-------------|")
        for p in params:
            req = "Yes" if p.required else "No"
            lines.append(f"| {p.name} | {p.type} | {req} | {p.description} |")
        lines.append("")

    @staticmethod
    def _render_response_fields(lines: list[str], fields: list[str]):
        if not fields:
            return
        lines.append("## Response Fields")
        lines.append("")
        lines.append("| Field | Type | Description |")
        lines.append("|-------|------|-------------|")
        for f in fields:
            lines.append(f"| {f} | | |")
        lines.append("")

    @staticmethod
    def _render_examples(lines: list[str], examples):
        lines.append("## Example Response")
        lines.append("")
        if examples:
            lines.append("```json")
            lines.append(json.dumps(examples, indent=2, ensure_ascii=False))
            lines.append("```")
        else:
            lines.append("> TODO: Add example response")
        lines.append("")

    @staticmethod
    def _render_notes(lines: list[str]):
        lines.append("## Notes")
        lines.append("")
        lines.append("> TODO: Add usage notes and tips")
```

注意：对于多 endpoint guide，参数/字段的 section 标题改为 `###`（三级，因为 `##` 被 method 占了）。更新 `_render_params` 和 `_render_response_fields` 需要接受 heading level 参数，或者在 multi-endpoint 渲染中用不同的方法。

实际实现时，让 `_render_params` 和 `_render_response_fields` 接受一个 `heading` 参数：

```python
    @staticmethod
    def _render_params(lines: list[str], params: list[ParamInfo], heading: str = "##"):
        if not params:
            return
        lines.append(f"{heading} Parameters")
        # ... rest same

    @staticmethod
    def _render_response_fields(lines: list[str], fields: list[str], heading: str = "##"):
        if not fields:
            return
        lines.append(f"{heading} Response Fields")
        # ... rest same

    @staticmethod
    def _render_examples(lines: list[str], examples, heading: str = "##"):
        lines.append(f"{heading} Example Response")
        # ... rest same
```

单 endpoint 时传 `"##"`，多 endpoint 时传 `"###"`。

- [ ] **Step 4: 运行测试**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv run pytest tests/test_import_openapi.py -v`
Expected: 全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/docchat/importers/openapi.py tests/test_import_openapi.py
git commit -m "feat: 文件生成器 — META.yaml + GUIDE.md 生成、冲突处理"
```

---

## Chunk 3: CLI 集成

### Task 6: CLI import 命令

**Files:**
- Modify: `src/docchat/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 写 CLI 测试**

```python
# 追加到 tests/test_cli.py

import json


TINY_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Tiny", "version": "1.0.0"},
    "paths": {
        "/items": {
            "get": {
                "operationId": "listItems",
                "summary": "List items",
                "responses": {"200": {"description": "OK"}},
            }
        }
    },
}


def test_import_noninteractive(tmp_path):
    """Test import with --yes flag (non-interactive)."""
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(TINY_SPEC))

    target = tmp_path / "pack"
    target.mkdir()
    (target / "docchat.yaml").write_text("name: test\ndimensions: []\n")
    (target / "feeds").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        main, ["import", str(spec_path), "--dir", str(target), "--yes", "--group", "endpoint"]
    )
    assert result.exit_code == 0
    assert (target / "feeds" / "list-items" / "META.yaml").exists()
    assert (target / "feeds" / "list-items" / "GUIDE.md").exists()


def test_import_creates_pack_if_missing(tmp_path):
    """If no docchat.yaml, import should init first."""
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(TINY_SPEC))

    target = tmp_path / "new-pack"

    runner = CliRunner()
    result = runner.invoke(
        main, ["import", str(spec_path), "--dir", str(target), "--yes", "--group", "endpoint"]
    )
    assert result.exit_code == 0
    assert (target / "docchat.yaml").exists()
    assert (target / "feeds" / "list-items" / "META.yaml").exists()


def test_import_skip_existing(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(TINY_SPEC))

    target = tmp_path / "pack"
    target.mkdir()
    (target / "docchat.yaml").write_text("name: test\ndimensions: []\n")
    feeds_dir = target / "feeds"
    feeds_dir.mkdir()
    (feeds_dir / "list-items").mkdir()
    (feeds_dir / "list-items" / "META.yaml").write_text("existing: true\n")

    runner = CliRunner()
    result = runner.invoke(
        main, ["import", str(spec_path), "--dir", str(target), "--yes", "--group", "endpoint"]
    )
    assert result.exit_code == 0
    # Should skip and not overwrite
    content = (feeds_dir / "list-items" / "META.yaml").read_text()
    assert "existing: true" in content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv run pytest tests/test_cli.py -v -k "import"`
Expected: FAIL — `No such command 'import'`

- [ ] **Step 3: 实现 CLI import 命令**

在 `src/docchat/cli.py` 追加：

```python
@main.command(name="import")
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--dir", "target_dir", default=".", help="Target knowledge pack directory")
@click.option("--group", type=click.Choice(["endpoint", "resource"]), default=None,
              help="Feed grouping granularity")
@click.option("--yes", is_flag=True, help="Non-interactive mode, skip existing feeds")
def import_cmd(spec_file: str, target_dir: str, group: str | None, yes: bool):
    """Import feeds from an OpenAPI spec file."""
    from rich.console import Console
    from docchat.importers.openapi import OpenAPIImporter

    console = Console()
    spec_path = Path(spec_file)
    target = Path(target_dir)

    # Parse spec
    try:
        importer = OpenAPIImporter(spec_path)
        importer.parse()
    except (ValueError, json.JSONDecodeError, yaml.YAMLError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    console.print(
        f"[green]📄 Parsed:[/green] {spec_path.name}"
        f"   Found {importer.endpoint_count} endpoints"
        f" across {importer.resource_count} resources"
    )

    # Determine grouping
    if group is None:
        if yes:
            group = "endpoint"
        else:
            import questionary
            group = questionary.select(
                "How to group endpoints into feeds?",
                choices=[
                    questionary.Choice(
                        f"One feed per endpoint ({importer.endpoint_count} feeds)",
                        value="endpoint",
                    ),
                    questionary.Choice(
                        f"One feed per resource ({importer.resource_count} feeds)",
                        value="resource",
                    ),
                ],
            ).ask()
            if group is None:
                raise SystemExit(0)

    feeds = (
        importer.group_by_endpoint()
        if group == "endpoint"
        else importer.group_by_resource()
    )

    # Determine target directory
    if not yes and target == Path("."):
        import questionary
        target_str = questionary.path(
            "Target directory?",
            default="./",
        ).ask()
        if target_str is None:
            raise SystemExit(0)
        target = Path(target_str)

    # Ensure pack exists
    config_path = target / "docchat.yaml"
    if not config_path.exists():
        if not yes:
            import questionary
            create = questionary.confirm(
                "No docchat.yaml found. Create a new pack?",
                default=True,
            ).ask()
            if not create:
                raise SystemExit(0)
        # Auto-init
        target.mkdir(parents=True, exist_ok=True)
        pack_name = spec_path.stem
        _init_pack(target, pack_name)
        console.print(f"[dim]Initialized pack '{pack_name}'[/dim]")

    # Determine feeds directory
    feeds_dir = target / "feeds"
    feeds_dir.mkdir(exist_ok=True)

    # Conflict handler
    def on_conflict(code: str) -> str:
        if yes:
            return "skip"
        import questionary
        overwrite = questionary.confirm(
            f"  ⚠ {code}/ already exists. Overwrite?",
            default=False,
        ).ask()
        return "overwrite" if overwrite else "skip"

    # Generate
    result = importer.generate(feeds, feeds_dir, on_conflict=on_conflict)

    # Report
    for code in result.created:
        console.print(f"  [green]✓[/green] {code}/")
    for code in result.skipped:
        console.print(f"  [yellow]⊘[/yellow] {code}/ — skipped")
    for code in result.overwritten:
        console.print(f"  [blue]↻[/blue] {code}/ — overwritten")

    total = len(result.created) + len(result.overwritten)
    console.print(
        f"\n[green]✓[/green] Generated {total} feeds"
        + (f", skipped {len(result.skipped)}" if result.skipped else "")
    )
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print("  1. Add trigger keywords to each META.yaml")
    console.print("  2. Review and enrich GUIDE.md files")
    console.print("  3. Run [bold]docchat validate[/bold] to check")


def _init_pack(target: Path, name: str):
    """Minimal pack initialization (reused from init command)."""
    config = {
        "name": name,
        "display_name": name,
        "version": "0.1.0",
        "description": "",
        "dimensions": [],
        "assistant": {
            "name": "API Assistant",
            "preamble_en": (
                "You are an API technical support assistant. "
                "Answer based on the documentation below."
            ),
            "preamble_zh": "你是 API 技术支持助手。请基于以下文档信息回答用户的问题。",
        },
    }
    (target / "docchat.yaml").write_text(
        yaml.dump(config, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    (target / "feeds").mkdir(exist_ok=True)
    shared_dir = target / "_shared"
    shared_dir.mkdir(exist_ok=True)
    (shared_dir / "INDEX.yaml").write_text(
        "topics:\n  - path: error_codes.md\n    keywords: [error, error code, status code]\n",
        encoding="utf-8",
    )
    (shared_dir / "error_codes.md").write_text(
        "# Error Codes\n\n| Code | Description |\n|------|-------------|\n"
        "| 400  | Bad Request |\n| 401  | Unauthorized |\n| 404  | Not Found |\n",
        encoding="utf-8",
    )
    overview_dir = target / "_overview"
    overview_dir.mkdir(exist_ok=True)
    (overview_dir / "INDEX.md").write_text(
        f"# {name} Overview\n\n## Available Feeds\n\nAdd feeds under `feeds/`.\n",
        encoding="utf-8",
    )
```

注意：需要在文件顶部加 `import json`（如果还没有的话），并且把 `_init_pack` 提取为独立函数，同时重构原有的 `init` 命令复用它。

- [ ] **Step 4: 运行测试**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv run pytest tests/test_cli.py -v`
Expected: 全部 PASSED（包括新旧测试）

- [ ] **Step 5: 运行全量测试确保无回归**

Run: `cd /Users/klauden/Documents/Projects/docchat-mcp && uv run pytest tests/ -v`
Expected: 全部 PASSED

- [ ] **Step 6: Commit**

```bash
git add src/docchat/cli.py tests/test_cli.py
git commit -m "feat: CLI import 命令 — 交互式/非交互式 OpenAPI 导入"
```

---

## Chunk 4: 手动验收

### Task 7: 用 demo spec 端到端测试

- [ ] **Step 1: 用 Petstore spec 手动测试 endpoint 粒度**

Run:
```bash
cd /Users/klauden/Documents/Projects/docchat-mcp
# 下载 petstore spec
curl -o /tmp/petstore.json https://petstore3.swagger.io/api/v3/openapi.json
# 导入
uv run docchat import /tmp/petstore.json --dir /tmp/test-pack --yes --group endpoint
# 检查生成结果
ls /tmp/test-pack/feeds/
cat /tmp/test-pack/feeds/*/META.yaml | head -50
```

Expected: feeds 目录下生成多个子目录，每个包含 META.yaml + GUIDE.md

- [ ] **Step 2: 测试 resource 粒度**

Run:
```bash
rm -rf /tmp/test-pack-resource
uv run docchat import /tmp/petstore.json --dir /tmp/test-pack-resource --yes --group resource
ls /tmp/test-pack-resource/feeds/
```

Expected: feeds 按 tag 分组，数量少于 endpoint 粒度

- [ ] **Step 3: 验证生成的包能正常 build**

Run:
```bash
uv run docchat build --dir /tmp/test-pack
uv run docchat validate --dir /tmp/test-pack
```

Expected: build 成功，validate 会有 triggers.keywords 空的警告（预期行为）

- [ ] **Step 4: 清理临时文件**

```bash
rm -rf /tmp/test-pack /tmp/test-pack-resource /tmp/petstore.json
```
