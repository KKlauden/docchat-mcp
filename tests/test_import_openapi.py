"""Tests for the OpenAPI importer module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from docchat.importers.openapi import (
    OpenAPIImporter,
    _extract_fields,
    _resolve_refs,
    _slugify,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def spec_file(tmp_path: Path):
    """Factory fixture: write a dict as JSON to a temp file and return its Path."""

    def _make(spec: dict[str, Any], suffix: str = ".json") -> Path:
        p = tmp_path / f"spec{suffix}"
        if suffix in {".yaml", ".yml"}:
            p.write_text(yaml.dump(spec), encoding="utf-8")
        else:
            p.write_text(json.dumps(spec), encoding="utf-8")
        return p

    return _make


def _minimal_spec(paths: dict | None = None, **extra) -> dict[str, Any]:
    """Build a minimal valid OAS 3.0 spec."""
    spec: dict[str, Any] = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": paths or {},
    }
    spec.update(extra)
    return spec


# ---------------------------------------------------------------------------
# 1. $ref resolution
# ---------------------------------------------------------------------------


def test_ref_resolution(spec_file):
    spec = _minimal_spec(
        paths={
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List users",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    },
                }
            }
        },
        **{
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                        },
                    }
                }
            }
        },
    )
    importer = OpenAPIImporter(spec_file(spec)).parse()
    skeletons = importer.group_by_endpoint()
    assert len(skeletons) == 1
    fields = skeletons[0].fields
    assert "id" in fields
    assert "name" in fields
    assert "email" in fields


# ---------------------------------------------------------------------------
# 2. Circular ref protection
# ---------------------------------------------------------------------------


def test_circular_ref_no_crash(spec_file):
    spec = _minimal_spec(
        paths={
            "/nodes": {
                "get": {
                    "operationId": "getNode",
                    "summary": "Get node",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Node"}
                                }
                            }
                        }
                    },
                }
            }
        },
        **{
            "components": {
                "schemas": {
                    "Node": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            # self-referential child
                            "child": {"$ref": "#/components/schemas/Node"},
                        },
                    }
                }
            }
        },
    )
    # Must not raise; circular child becomes placeholder
    importer = OpenAPIImporter(spec_file(spec)).parse()
    skeletons = importer.group_by_endpoint()
    assert len(skeletons) == 1
    fields = skeletons[0].fields
    assert "id" in fields
    assert "name" in fields


# ---------------------------------------------------------------------------
# 3. allOf merge
# ---------------------------------------------------------------------------


def test_allof_merge():
    root = {
        "components": {
            "schemas": {
                "A": {"type": "object", "properties": {"foo": {"type": "string"}}},
                "B": {"type": "object", "properties": {"bar": {"type": "integer"}}},
            }
        }
    }
    schema = {
        "allOf": [
            {"$ref": "#/components/schemas/A"},
            {"$ref": "#/components/schemas/B"},
        ]
    }
    resolved = _resolve_refs(schema, root)
    assert "properties" in resolved
    assert "foo" in resolved["properties"]
    assert "bar" in resolved["properties"]


# ---------------------------------------------------------------------------
# 4. YAML format
# ---------------------------------------------------------------------------


def test_parse_yaml_format(spec_file):
    spec = _minimal_spec(
        paths={
            "/items": {
                "get": {
                    "operationId": "listItems",
                    "summary": "List items",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )
    importer = OpenAPIImporter(spec_file(spec, suffix=".yaml")).parse()
    assert importer.endpoint_count == 1


# ---------------------------------------------------------------------------
# 5. Empty paths → ValueError
# ---------------------------------------------------------------------------


def test_parse_empty_paths(spec_file):
    spec = _minimal_spec(paths={})
    with pytest.raises(ValueError, match="no paths"):
        OpenAPIImporter(spec_file(spec)).parse()


# ---------------------------------------------------------------------------
# 6. Unknown version → ValueError
# ---------------------------------------------------------------------------


def test_unknown_version(spec_file):
    spec = {"info": {"title": "Bad"}, "paths": {"/x": {}}}
    with pytest.raises(ValueError, match="Unknown spec format"):
        OpenAPIImporter(spec_file(spec)).parse()


# ---------------------------------------------------------------------------
# 7. Swagger 2.0 compat
# ---------------------------------------------------------------------------


def test_swagger2_compat(spec_file):
    spec: dict[str, Any] = {
        "swagger": "2.0",
        "info": {"title": "Old API", "version": "1.0"},
        "basePath": "/v1",
        "definitions": {
            "Pet": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            }
        },
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "listPets",
                    "summary": "List pets",
                    "responses": {
                        "200": {
                            "description": "ok",
                            "schema": {"$ref": "#/definitions/Pet"},
                        }
                    },
                }
            }
        },
    }
    importer = OpenAPIImporter(spec_file(spec)).parse()
    assert importer.endpoint_count == 1
    ep = importer._endpoints[0]
    # basePath must be prepended
    assert ep.path.startswith("/v1")
    # definitions resolved → fields extracted
    skeletons = importer.group_by_endpoint()
    assert "id" in skeletons[0].fields or "name" in skeletons[0].fields


# ---------------------------------------------------------------------------
# 8. feed_code with operationId
# ---------------------------------------------------------------------------


def test_feed_code_with_operation_id(spec_file):
    spec = _minimal_spec(
        paths={
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List users",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )
    importer = OpenAPIImporter(spec_file(spec)).parse()
    skeletons = importer.group_by_endpoint()
    assert skeletons[0].feed_code == "list-users"


# ---------------------------------------------------------------------------
# 9. feed_code without operationId
# ---------------------------------------------------------------------------


def test_feed_code_without_operation_id(spec_file):
    spec = _minimal_spec(
        paths={
            "/users/{id}": {
                "get": {
                    "summary": "Get user by id",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )
    importer = OpenAPIImporter(spec_file(spec)).parse()
    skeletons = importer.group_by_endpoint()
    fc = skeletons[0].feed_code
    assert "get" in fc
    assert "users" in fc


# ---------------------------------------------------------------------------
# 10. Wrapper response fields
# ---------------------------------------------------------------------------


def test_wrapper_response_fields():
    schema = {
        "type": "object",
        "properties": {
            "total": {"type": "integer"},
            "data": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "userId": {"type": "integer"},
                        "userName": {"type": "string"},
                    },
                },
            },
        },
    }
    fields = _extract_fields(schema)
    assert "userId" in fields
    assert "userName" in fields
    # top-level wrapper key should NOT appear
    assert "data" not in fields


# ---------------------------------------------------------------------------
# 11. Example from spec
# ---------------------------------------------------------------------------


def test_example_from_spec(spec_file):
    spec = _minimal_spec(
        paths={
            "/ping": {
                "get": {
                    "operationId": "ping",
                    "summary": "Ping",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"},
                                    "example": {"pong": True},
                                }
                            }
                        }
                    },
                }
            }
        }
    )
    importer = OpenAPIImporter(spec_file(spec)).parse()
    ep = importer._endpoints[0]
    assert ep.response_examples.get("default") == {"pong": True}


# ---------------------------------------------------------------------------
# 12. External $ref does not crash
# ---------------------------------------------------------------------------


def test_external_ref_skip():
    root: dict[str, Any] = {}
    obj = {"$ref": "https://example.com/schemas/Foo"}
    result = _resolve_refs(obj, root)
    assert result.get("description") == "(external ref)"


# ---------------------------------------------------------------------------
# 13. group_by_endpoint count
# ---------------------------------------------------------------------------


def test_group_by_endpoint_count(spec_file):
    spec = _minimal_spec(
        paths={
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List",
                    "responses": {"200": {"description": "ok"}},
                },
                "post": {
                    "operationId": "createUser",
                    "summary": "Create",
                    "responses": {"201": {"description": "created"}},
                },
            },
            "/users/{id}": {
                "get": {
                    "operationId": "getUser",
                    "summary": "Get one",
                    "responses": {"200": {"description": "ok"}},
                }
            },
        }
    )
    importer = OpenAPIImporter(spec_file(spec)).parse()
    assert importer.endpoint_count == 3
    skeletons = importer.group_by_endpoint()
    assert len(skeletons) == 3


# ---------------------------------------------------------------------------
# 14. group_by_resource with tags
# ---------------------------------------------------------------------------


def test_group_by_resource_with_tags(spec_file):
    spec = _minimal_spec(
        paths={
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "tags": ["users"],
                    "summary": "List users",
                    "responses": {"200": {"description": "ok"}},
                }
            },
            "/posts": {
                "get": {
                    "operationId": "listPosts",
                    "tags": ["posts"],
                    "summary": "List posts",
                    "responses": {"200": {"description": "ok"}},
                }
            },
        }
    )
    importer = OpenAPIImporter(spec_file(spec)).parse()
    skeletons = importer.group_by_resource()
    codes = {s.feed_code for s in skeletons}
    assert "users" in codes
    assert "posts" in codes


# ---------------------------------------------------------------------------
# 15. group_by_resource merges fields
# ---------------------------------------------------------------------------


def test_group_by_resource_merges_fields(spec_file):
    spec = _minimal_spec(
        paths={
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "tags": ["users"],
                    "summary": "List users",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    },
                },
                "post": {
                    "operationId": "createUser",
                    "tags": ["users"],
                    "summary": "Create user",
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "email": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    },
                },
            }
        }
    )
    importer = OpenAPIImporter(spec_file(spec)).parse()
    skeletons = importer.group_by_resource()
    assert len(skeletons) == 1
    fields = skeletons[0].fields
    assert "id" in fields
    assert "name" in fields
    assert "email" in fields


# ---------------------------------------------------------------------------
# 16. Resource grouping without tags (path prefix)
# ---------------------------------------------------------------------------


def test_resource_grouping_no_tags(spec_file):
    spec = _minimal_spec(
        paths={
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List users",
                    "responses": {"200": {"description": "ok"}},
                }
            },
            "/users/{id}": {
                "get": {
                    "operationId": "getUser",
                    "summary": "Get user",
                    "responses": {"200": {"description": "ok"}},
                }
            },
            "/posts": {
                "get": {
                    "operationId": "listPosts",
                    "summary": "List posts",
                    "responses": {"200": {"description": "ok"}},
                }
            },
        }
    )
    importer = OpenAPIImporter(spec_file(spec)).parse()
    # Without tags, path-prefix grouping applies
    skeletons = importer.group_by_resource()
    # Should produce at least 2 distinct groups (users-related + posts)
    assert len(skeletons) >= 2


# ---------------------------------------------------------------------------
# Shared spec dicts for generate() tests
# ---------------------------------------------------------------------------

MINIMAL_SPEC_3 = _minimal_spec(
    paths={
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List pets",
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                    },
                                }
                            }
                        }
                    }
                },
            },
            "post": {
                "operationId": "createPet",
                "tags": ["pets"],
                "summary": "Create pet",
                "responses": {"201": {"description": "created"}},
            },
        },
        "/pets/{id}": {
            "get": {
                "operationId": "getPet",
                "tags": ["pets"],
                "summary": "Get pet",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Pet identifier",
                    }
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
    }
)

EXAMPLE_IN_SPEC = _minimal_spec(
    paths={
        "/status": {
            "get": {
                "operationId": "getStatus",
                "summary": "Get status",
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"},
                                "example": {"status": "ok", "version": "1.0"},
                            }
                        }
                    }
                },
            }
        }
    }
)


# ---------------------------------------------------------------------------
# 17. generate() creates feed dirs and files
# ---------------------------------------------------------------------------


def test_generate_creates_feed_dirs(spec_file, tmp_path):
    """generate() 为每个 feed 创建目录、META.yaml 和 GUIDE.md。"""
    p = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(p).parse()
    feeds = importer.group_by_endpoint()
    out_dir = tmp_path / "output"

    result = importer.generate(feeds, out_dir, on_conflict=lambda fc: "skip")

    assert len(result.created) == len(feeds)
    assert result.skipped == []
    assert result.overwritten == []

    for feed in feeds:
        feed_dir = out_dir / feed.feed_code
        assert feed_dir.is_dir(), f"目录不存在: {feed_dir}"
        assert (feed_dir / "META.yaml").exists()
        assert (feed_dir / "GUIDE.md").exists()


# ---------------------------------------------------------------------------
# 18. META.yaml 内容正确
# ---------------------------------------------------------------------------


def test_generate_meta_content(spec_file, tmp_path):
    """META.yaml 中 name、feed_name、endpoint、triggers.keywords、fields 均正确。"""
    import yaml

    p = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(p).parse()
    feeds = importer.group_by_endpoint()
    out_dir = tmp_path / "output"
    importer.generate(feeds, out_dir, on_conflict=lambda fc: "skip")

    # 检查 listPets feed 的 META.yaml
    list_pets_feed = next(f for f in feeds if f.feed_code == "list-pets")
    meta_path = out_dir / "list-pets" / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))

    assert meta["name"] == "list-pets"
    assert meta["feed_name"] == "List pets"
    assert "GET" in meta["endpoint"]
    assert "/pets" in meta["endpoint"]
    assert meta["triggers"]["keywords"] == []
    assert meta["triggers"]["scenarios"] == []
    assert isinstance(meta["fields"], list)
    # id 和 name 应在 fields 中
    assert "id" in meta["fields"]
    assert "name" in meta["fields"]


# ---------------------------------------------------------------------------
# 19. GUIDE.md 包含必要 section
# ---------------------------------------------------------------------------


def test_generate_guide_content(spec_file, tmp_path):
    """GUIDE.md 包含标题、## Parameters、## Response Fields。"""
    p = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(p).parse()
    feeds = importer.group_by_endpoint()
    out_dir = tmp_path / "output"
    importer.generate(feeds, out_dir, on_conflict=lambda fc: "skip")

    guide = (out_dir / "list-pets" / "GUIDE.md").read_text(encoding="utf-8")
    assert "# List pets" in guide
    assert "## Parameters" in guide
    assert "## Response Fields" in guide


# ---------------------------------------------------------------------------
# 20. spec 中有 example 时写入 GUIDE.md
# ---------------------------------------------------------------------------


def test_generate_with_example(spec_file, tmp_path):
    """spec 中内联 example 时，GUIDE.md 包含该 example 的值。"""
    p = spec_file(EXAMPLE_IN_SPEC)
    importer = OpenAPIImporter(p).parse()
    feeds = importer.group_by_endpoint()
    out_dir = tmp_path / "output"
    importer.generate(feeds, out_dir, on_conflict=lambda fc: "skip")

    guide = (out_dir / "get-status" / "GUIDE.md").read_text(encoding="utf-8")
    assert "ok" in guide  # example 中的 "status": "ok"
    assert "1.0" in guide  # example 中的 "version": "1.0"


# ---------------------------------------------------------------------------
# 21. 冲突时 skip 保留原文件
# ---------------------------------------------------------------------------


def test_generate_skip_existing(spec_file, tmp_path):
    """on_conflict 返回 'skip' 时，原文件内容不被覆盖。"""
    p = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(p).parse()
    feeds = importer.group_by_endpoint()
    out_dir = tmp_path / "output"

    # 先创建一个 feed 目录，写入占位内容
    feed = feeds[0]
    feed_dir = out_dir / feed.feed_code
    feed_dir.mkdir(parents=True)
    original_content = "ORIGINAL CONTENT"
    (feed_dir / "GUIDE.md").write_text(original_content, encoding="utf-8")

    result = importer.generate(feeds, out_dir, on_conflict=lambda fc: "skip")

    # 该 feed 应被 skip
    assert feed.feed_code in result.skipped
    # 原文件内容未改变
    assert (feed_dir / "GUIDE.md").read_text(encoding="utf-8") == original_content


# ---------------------------------------------------------------------------
# 22. 冲突时 overwrite 覆盖文件
# ---------------------------------------------------------------------------


def test_generate_overwrite_existing(spec_file, tmp_path):
    """on_conflict 返回 'overwrite' 时，文件被新内容覆盖。"""
    p = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(p).parse()
    feeds = importer.group_by_endpoint()
    out_dir = tmp_path / "output"

    # 先创建一个 feed 目录，写入占位内容
    feed = feeds[0]
    feed_dir = out_dir / feed.feed_code
    feed_dir.mkdir(parents=True)
    original_content = "ORIGINAL CONTENT"
    (feed_dir / "GUIDE.md").write_text(original_content, encoding="utf-8")

    result = importer.generate(feeds, out_dir, on_conflict=lambda fc: "overwrite")

    # 该 feed 应被 overwrite
    assert feed.feed_code in result.overwritten
    # 文件内容已被新生成的内容替换
    new_content = (feed_dir / "GUIDE.md").read_text(encoding="utf-8")
    assert new_content != original_content
    assert "#" in new_content  # Markdown 标题


# ---------------------------------------------------------------------------
# 23. 资源粒度 GUIDE.md 按 method 分 section
# ---------------------------------------------------------------------------


def test_generate_resource_guide_multi_endpoint(spec_file, tmp_path):
    """group_by_resource 生成的 GUIDE.md 按 HTTP method 分 ## section。"""
    p = spec_file(MINIMAL_SPEC_3)
    importer = OpenAPIImporter(p).parse()
    feeds = importer.group_by_resource()
    out_dir = tmp_path / "output"
    importer.generate(feeds, out_dir, on_conflict=lambda fc: "skip")

    # pets 资源 feed 应有多个 endpoint（GET /pets, POST /pets, GET /pets/{id}）
    pets_feed = next(f for f in feeds if f.feed_code == "pets")
    guide = (out_dir / "pets" / "GUIDE.md").read_text(encoding="utf-8")

    # 多 endpoint 时使用 ## METHOD /path 格式
    assert "## GET /pets" in guide or "## POST /pets" in guide
