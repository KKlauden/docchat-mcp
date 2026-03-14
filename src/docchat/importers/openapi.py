"""OpenAPI / Swagger specification importer."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ParamInfo:
    """Single API parameter."""

    name: str
    type: str
    required: bool
    description: str
    location: str  # query / path / header / cookie / body


@dataclass
class EndpointInfo:
    """Parsed representation of one API operation."""

    method: str
    path: str
    operation_id: str
    summary: str
    description: str
    parameters: list[ParamInfo]
    request_body: dict[str, Any]
    response_schema: dict[str, Any]
    response_examples: dict[str, Any]
    tags: list[str]


@dataclass
class FeedSkeleton:
    """A logical feed grouping one or more endpoints."""

    feed_code: str
    feed_name: str
    description: str
    endpoints: list[EndpointInfo]
    fields: list[str]
    parameters: list[ParamInfo]
    examples: dict[str, Any]


@dataclass
class GenerateResult:
    """Result of a file-generation pass."""

    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    overwritten: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert camelCase / PascalCase / arbitrary text to kebab-case.

    Examples::

        >>> _slugify("listUsers")
        'list-users'
        >>> _slugify("GetUserById")
        'get-user-by-id'
        >>> _slugify("/users/{id}/posts")
        'users-id-posts'
    """
    # Insert a hyphen before every uppercase letter that follows a lowercase
    # letter or digit (handles camelCase and PascalCase).
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", text)
    # Replace any non-alphanumeric characters with hyphens.
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s)
    # Collapse multiple hyphens and strip leading/trailing ones.
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s.lower()


def _resolve_refs(
    obj: Any,
    root: dict[str, Any],
    visited: set[str] | None = None,
) -> Any:
    """Recursively resolve JSON Pointer ``$ref`` references.

    - Circular references are protected via *visited* set; when detected a
      placeholder ``{"type": "object", "description": "(circular ref)"}`` is
      returned.
    - External ``$ref`` values (not starting with ``#/``) are skipped and
      replaced with ``{"type": "object", "description": "(external ref)"}``.
    - ``allOf`` schemas are merged by flattening all ``properties`` dicts.
    - ``oneOf`` / ``anyOf`` collapse to the first schema.
    """
    if visited is None:
        visited = set()

    if not isinstance(obj, (dict, list)):
        return obj

    if isinstance(obj, list):
        return [_resolve_refs(item, root, visited) for item in obj]

    # --- dict from here ---

    # Handle $ref first
    if "$ref" in obj:
        ref: str = obj["$ref"]
        if not ref.startswith("#/"):
            # External ref — skip
            return {"type": "object", "description": "(external ref)"}
        if ref in visited:
            return {"type": "object", "description": "(circular ref)"}
        visited = visited | {ref}  # immutable update to avoid cross-branch pollution
        # Resolve JSON Pointer: "#/components/schemas/Foo" → ["components", "schemas", "Foo"]
        parts = ref.lstrip("#/").split("/")
        node: Any = root
        for part in parts:
            if not isinstance(node, dict):
                return {"type": "object", "description": "(unresolvable ref)"}
            node = node.get(part, {})
        return _resolve_refs(node, root, visited)

    # Handle allOf — merge all properties
    if "allOf" in obj:
        merged: dict[str, Any] = {}
        merged_props: dict[str, Any] = {}
        for sub in obj["allOf"]:
            resolved = _resolve_refs(sub, root, visited)
            if isinstance(resolved, dict):
                for k, v in resolved.items():
                    if k == "properties":
                        merged_props.update(v)
                    else:
                        merged[k] = v
        if merged_props:
            merged["properties"] = merged_props
        return merged

    # Handle oneOf / anyOf — take first
    for keyword in ("oneOf", "anyOf"):
        if keyword in obj:
            schemas = obj[keyword]
            if schemas:
                return _resolve_refs(schemas[0], root, visited)
            return {"type": "object"}

    # Recurse into dict values
    return {k: _resolve_refs(v, root, visited) for k, v in obj.items()}


def _extract_fields(schema: dict[str, Any]) -> list[str]:
    """Extract field names from a resolved response schema.

    Strategy:
    1. If schema is ``array`` with ``items``, use the items schema.
    2. For ``object`` schemas with ``properties``, check for wrapper keys
       (``data`` / ``items`` / ``results`` / ``records`` / ``rows`` / ``list``).
       If a wrapper key maps to an array-with-items or object-with-properties,
       expand one level and return the inner fields.
    3. Otherwise return the top-level property keys.
    """
    if not isinstance(schema, dict):
        return []

    # Unwrap array at the top level
    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        schema = schema["items"]

    props: dict[str, Any] = schema.get("properties", {})
    if not props:
        return []

    _WRAPPERS = {"data", "items", "results", "records", "rows", "list"}

    for wrapper_key in _WRAPPERS:
        if wrapper_key not in props:
            continue
        inner = props[wrapper_key]
        if not isinstance(inner, dict):
            continue
        # array wrapper with items
        if inner.get("type") == "array" and isinstance(inner.get("items"), dict):
            inner_props = inner["items"].get("properties", {})
            if inner_props:
                return list(inner_props.keys())
        # object wrapper with properties
        if inner.get("type") == "object" or "properties" in inner:
            inner_props = inner.get("properties", {})
            if inner_props:
                return list(inner_props.keys())

    return list(props.keys())


def _generate_example(schema: dict[str, Any]) -> Any:
    """Generate a skeleton example value from a JSON Schema dict."""
    if not isinstance(schema, dict):
        return None

    typ = schema.get("type", "object")

    if typ == "string":
        return schema.get("example", "string")
    if typ == "integer":
        return schema.get("example", 0)
    if typ == "number":
        return schema.get("example", 0.0)
    if typ == "boolean":
        return schema.get("example", True)
    if typ == "array":
        items = schema.get("items", {})
        return [_generate_example(items)]
    # object / fallback
    props = schema.get("properties", {})
    return {k: _generate_example(v) for k, v in props.items()}


# ---------------------------------------------------------------------------
# Main importer class
# ---------------------------------------------------------------------------


class OpenAPIImporter:
    """Parse an OpenAPI 3.x or Swagger 2.0 specification file."""

    def __init__(self, spec_path: str | Path) -> None:
        self._spec_path = Path(spec_path)
        self._spec: dict[str, Any] = {}
        self._endpoints: list[EndpointInfo] = []
        self._parsed = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> "OpenAPIImporter":
        """Load and parse the spec file.  Returns *self* for chaining."""
        raw = self._spec_path.read_text(encoding="utf-8")
        if self._spec_path.suffix in {".yaml", ".yml"}:
            import yaml  # lazy import

            data: dict[str, Any] = yaml.safe_load(raw)
        else:
            data = json.loads(raw)

        # Version detection
        if "openapi" in data:
            version_str: str = str(data["openapi"])
            if not version_str.startswith("3"):
                raise ValueError(f"Unsupported OpenAPI version: {version_str}")
        elif "swagger" in data:
            version_str = str(data["swagger"])
            if not version_str.startswith("2"):
                raise ValueError(f"Unsupported Swagger version: {version_str}")
            self._normalize_swagger2(data)
        else:
            raise ValueError(
                "Unknown spec format: missing 'openapi' or 'swagger' field."
            )

        paths = data.get("paths", {})
        if not paths:
            raise ValueError("Spec contains no paths.")

        self._spec = data
        self._endpoints = self._extract_endpoints()
        self._parsed = True
        return self

    @property
    def endpoint_count(self) -> int:
        """Number of parsed endpoints (operations)."""
        return len(self._endpoints)

    @property
    def resource_count(self) -> int:
        """Number of distinct resource groups (by tag / path prefix)."""
        groups = self._group_by_tag_or_path()
        return len(groups)

    def group_by_endpoint(self) -> list[FeedSkeleton]:
        """One FeedSkeleton per operation."""
        result: list[FeedSkeleton] = []
        for ep in self._endpoints:
            feed_code = self._endpoint_feed_code(ep)
            fields = _extract_fields(ep.response_schema)
            example = _generate_example(ep.response_schema)
            skeleton = FeedSkeleton(
                feed_code=feed_code,
                feed_name=ep.summary or feed_code,
                description=ep.description or ep.summary or "",
                endpoints=[ep],
                fields=fields,
                parameters=ep.parameters,
                examples={"default": example} if example is not None else {},
            )
            result.append(skeleton)
        return result

    def group_by_resource(self) -> list[FeedSkeleton]:
        """One FeedSkeleton per resource group (tag or path prefix)."""
        groups = self._group_by_tag_or_path()
        result: list[FeedSkeleton] = []
        for key, endpoints in groups.items():
            # Merge fields from all endpoints
            all_fields: list[str] = []
            seen_fields: set[str] = set()
            all_params: list[ParamInfo] = []
            seen_params: set[str] = set()
            all_examples: dict[str, Any] = {}

            for ep in endpoints:
                for f in _extract_fields(ep.response_schema):
                    if f not in seen_fields:
                        all_fields.append(f)
                        seen_fields.add(f)
                for p in ep.parameters:
                    if p.name not in seen_params:
                        all_params.append(p)
                        seen_params.add(p.name)
                ex = _generate_example(ep.response_schema)
                if ex is not None:
                    all_examples[ep.operation_id or ep.path] = ex

            feed_code = _slugify(key)
            feed_name = key.replace("-", " ").replace("_", " ").title()
            description = endpoints[0].description or endpoints[0].summary or ""

            skeleton = FeedSkeleton(
                feed_code=feed_code,
                feed_name=feed_name,
                description=description,
                endpoints=endpoints,
                fields=all_fields,
                parameters=all_params,
                examples=all_examples,
            )
            result.append(skeleton)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rewrite_refs(obj: Any, old_prefix: str, new_prefix: str) -> Any:
        """Recursively rewrite $ref strings from old_prefix to new_prefix."""
        if isinstance(obj, dict):
            return {
                k: (
                    new_prefix + v[len(old_prefix):]
                    if k == "$ref" and isinstance(v, str) and v.startswith(old_prefix)
                    else OpenAPIImporter._rewrite_refs(v, old_prefix, new_prefix)
                )
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [OpenAPIImporter._rewrite_refs(i, old_prefix, new_prefix) for i in obj]
        return obj

    def _normalize_swagger2(self, data: dict[str, Any]) -> None:
        """In-place normalise a Swagger 2.0 spec to approximate OAS 3.x shape."""
        # definitions → components/schemas
        if "definitions" in data:
            data.setdefault("components", {})["schemas"] = data.pop("definitions")
            # Rewrite all $ref strings that pointed to #/definitions/
            rewritten = self._rewrite_refs(
                data.get("paths", {}),
                "#/definitions/",
                "#/components/schemas/",
            )
            data["paths"] = rewritten

        base_path: str = data.get("basePath", "")
        # Store basePath so _extract_endpoints can prepend it
        data["_basePath"] = base_path

        # Normalise responses and body parameters for each operation
        for path_item in data.get("paths", {}).values():
            for method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue
                # Body parameter → requestBody
                params: list[dict[str, Any]] = operation.get("parameters", [])
                non_body = []
                for p in params:
                    if p.get("in") == "body":
                        schema = p.get("schema", {})
                        operation["requestBody"] = {
                            "content": {"application/json": {"schema": schema}}
                        }
                    else:
                        non_body.append(p)
                if len(non_body) != len(params):
                    operation["parameters"] = non_body

                # Responses: inline schema → content wrapper
                for status, resp in operation.get("responses", {}).items():
                    if not isinstance(resp, dict):
                        continue
                    if "schema" in resp and "content" not in resp:
                        resp["content"] = {
                            "application/json": {"schema": resp.pop("schema")}
                        }

    def _extract_endpoints(self) -> list[EndpointInfo]:
        """Iterate paths and extract EndpointInfo objects."""
        endpoints: list[EndpointInfo] = []
        base_path: str = self._spec.get("_basePath", "")
        _HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
        _SUCCESS_CODES = {"200", "201", "202", "2XX"}

        for path_str, path_item in self._spec.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            # Path-level parameters
            path_params: list[dict[str, Any]] = path_item.get("parameters", [])

            full_path = base_path.rstrip("/") + path_str if base_path else path_str

            for method, operation in path_item.items():
                if method.lower() not in _HTTP_METHODS:
                    continue
                if not isinstance(operation, dict):
                    continue

                # Merge path-level + operation-level parameters (operation wins)
                op_params: list[dict[str, Any]] = operation.get("parameters", [])
                param_map: dict[tuple[str, str], dict[str, Any]] = {}
                for p in path_params:
                    param_map[(p.get("name", ""), p.get("in", ""))] = p
                for p in op_params:
                    param_map[(p.get("name", ""), p.get("in", ""))] = p

                parameters: list[ParamInfo] = []
                for p in param_map.values():
                    schema_node = p.get("schema", {})
                    param_type = schema_node.get("type", p.get("type", "string"))
                    parameters.append(
                        ParamInfo(
                            name=p.get("name", ""),
                            type=param_type,
                            required=bool(p.get("required", False)),
                            description=p.get("description", ""),
                            location=p.get("in", "query"),
                        )
                    )

                # Request body
                request_body: dict[str, Any] = operation.get("requestBody", {})

                # Response schema — first 2xx
                response_schema: dict[str, Any] = {}
                response_examples: dict[str, Any] = {}
                responses: dict[str, Any] = operation.get("responses", {})
                for code in _SUCCESS_CODES:
                    if code in responses:
                        resp = responses[code]
                        if not isinstance(resp, dict):
                            continue
                        content = resp.get("content", {})
                        json_content = content.get(
                            "application/json", next(iter(content.values()), {})
                        )
                        raw_schema = json_content.get("schema", {})
                        response_schema = _resolve_refs(raw_schema, self._spec)
                        # Examples
                        examples_node = json_content.get("examples", {})
                        if examples_node:
                            response_examples = examples_node
                        elif "example" in json_content:
                            response_examples = {"default": json_content["example"]}
                        break

                endpoints.append(
                    EndpointInfo(
                        method=method.upper(),
                        path=full_path,
                        operation_id=operation.get("operationId", ""),
                        summary=operation.get("summary", ""),
                        description=operation.get("description", ""),
                        parameters=parameters,
                        request_body=request_body,
                        response_schema=response_schema,
                        response_examples=response_examples,
                        tags=operation.get("tags", []),
                    )
                )
        return endpoints

    def _group_by_tag_or_path(self) -> dict[str, list[EndpointInfo]]:
        """Group endpoints by tag (primary) or path prefix (fallback)."""
        groups: dict[str, list[EndpointInfo]] = {}
        for ep in self._endpoints:
            key = (
                ep.tags[0]
                if ep.tags
                else self._path_to_resource_key(ep.path)
            )
            groups.setdefault(key, []).append(ep)
        return groups

    @staticmethod
    def _path_to_code(method: str, path: str) -> str:
        """Create a feed code from HTTP method + path."""
        slug = _slugify(path)
        return f"{method.lower()}-{slug}"

    @staticmethod
    def _path_to_resource_key(path: str) -> str:
        """Derive a resource key from a URL path.

        Takes the last non-parameter segment.  For multi-segment paths uses
        ``{parent}-{child}`` to avoid collisions.
        """
        # Strip query string just in case
        path = path.split("?")[0]
        # Split and filter out empty parts and path params like {id}
        parts = [p for p in path.strip("/").split("/") if p and not p.startswith("{")]
        if not parts:
            return "root"
        if len(parts) == 1:
            return parts[0]
        # Use last two non-param segments to create a qualified key
        return f"{parts[-2]}-{parts[-1]}"

    def _endpoint_feed_code(self, ep: EndpointInfo) -> str:
        """Derive a feed code for a single endpoint."""
        if ep.operation_id:
            return _slugify(ep.operation_id)
        return self._path_to_code(ep.method, ep.path)
