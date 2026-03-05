"""DocChat CLI — init / build / serve / mcp / validate."""

from pathlib import Path

import click
import yaml


@click.group()
def main():
    """DocChat - Turn API docs into an intelligent MCP server."""
    pass


@main.command()
@click.option("--dir", "target_dir", default=".", help="Target directory")
@click.option("--name", prompt="Knowledge pack name", help="Knowledge pack name")
def init(target_dir: str, name: str):
    """Initialize a knowledge pack (docchat.yaml + directory structure)."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    # docchat.yaml
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
    config_path = target / "docchat.yaml"
    config_path.write_text(
        yaml.dump(config, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )

    # feeds/
    feeds_dir = target / "feeds"
    feeds_dir.mkdir(exist_ok=True)

    # _shared/INDEX.yaml
    shared_dir = target / "_shared"
    shared_dir.mkdir(exist_ok=True)
    shared_index = {
        "topics": [
            {
                "path": "error_codes.md",
                "keywords": ["error", "error code", "status code"],
            },
        ],
    }
    (shared_dir / "INDEX.yaml").write_text(
        "# Shared knowledge topic index\n"
        "# Each topic has a path (relative to _shared/) and keywords for matching\n"
        "#\n"
        "# Example:\n"
        "#   topics:\n"
        "#     - path: auth/overview.md\n"
        "#       keywords: [authentication, auth, token]\n"
        "#     - path: error_codes.md\n"
        "#       keywords: [error, error code, status code]\n"
        "#       product: sdapi  # optional: filter by dimension value\n"
        "\n"
        + yaml.dump(shared_index, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    # Starter error_codes.md
    (shared_dir / "error_codes.md").write_text(
        "# Error Codes\n\n"
        "<!-- Add your API error codes and their descriptions here -->\n\n"
        "| Code | Description |\n"
        "|------|-------------|\n"
        "| 400  | Bad Request |\n"
        "| 401  | Unauthorized |\n"
        "| 404  | Not Found |\n"
        "| 500  | Internal Server Error |\n",
        encoding="utf-8",
    )

    # _overview/INDEX.md
    overview_dir = target / "_overview"
    overview_dir.mkdir(exist_ok=True)
    (overview_dir / "INDEX.md").write_text(
        f"# {name} Overview\n\n"
        "<!-- Describe your API here: what it does, how feeds are organized, etc. -->\n\n"
        "## Available Feeds\n\n"
        "Add your feeds under the `feeds/` directory. Each feed should have:\n\n"
        "- `META.yaml` — Feed metadata, trigger keywords, and field list\n"
        "- `GUIDE.md` — Usage guide\n"
        "- `FAQ.md` — Frequently asked questions (optional)\n"
        "- `fields/` — Field reference files (optional)\n",
        encoding="utf-8",
    )

    click.echo(f"Initialized knowledge pack '{name}' in {target.resolve()}")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  1. Add feed directories under {feeds_dir}/")
    click.echo("  2. Write META.yaml + GUIDE.md for each feed")
    click.echo("  3. Run: docchat validate")
    click.echo("  4. Run: docchat build")
    click.echo("  5. Run: docchat serve  (or: docchat mcp)")


@main.command()
@click.option("--dir", "pack_dir", default=".", help="Knowledge pack directory")
def build(pack_dir: str):
    """Build index (verify pack loads correctly)."""
    from docchat.engine.index_loader import KnowledgeEngine

    target = Path(pack_dir)
    engine = KnowledgeEngine(target)
    engine.load()

    feeds = engine.list_feeds()
    click.echo(f"Build successful: {len(feeds)} feeds indexed")
    for feed in feeds:
        click.echo(f"  [{feed['feed_code']}] {feed['feed_name']}")


@main.command()
@click.option("--dir", "pack_dir", default=".", help="Knowledge pack directory")
@click.option("--port", default=8000, help="HTTP port")
def serve(pack_dir: str, port: int):
    """Start MCP Server (HTTP mode)."""
    from docchat.mcp_server import create_mcp_server

    target = Path(pack_dir)
    mcp = create_mcp_server(target)
    click.echo(f"Starting MCP server on port {port}...")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)


@main.command("mcp")
@click.option("--dir", "pack_dir", default=".", help="Knowledge pack directory")
def mcp_stdio(pack_dir: str):
    """Start MCP Server (stdio mode, for Claude Code)."""
    from docchat.mcp_server import create_mcp_server

    target = Path(pack_dir)
    mcp = create_mcp_server(target)
    mcp.run(transport="stdio")


@main.command()
@click.option("--dir", "pack_dir", default=".", help="Knowledge pack directory")
def validate(pack_dir: str):
    """Validate knowledge pack format."""
    target = Path(pack_dir)

    # Check docchat.yaml exists
    config_path = target / "docchat.yaml"
    if not config_path.exists():
        click.echo(f"Error: No docchat.yaml found in {target.resolve()}", err=True)
        raise SystemExit(1)

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    click.echo(f"Pack: {config.get('name', '(unnamed)')}")

    # Find feed directories
    feeds_dir = target / "feeds"
    warnings = 0
    feed_count = 0

    if feeds_dir.is_dir():
        for child in sorted(feeds_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("_"):
                continue
            meta_path = child / "META.yaml"
            if not meta_path.exists():
                click.echo(f"  Warning: {child.name}/ has no META.yaml")
                warnings += 1
                continue

            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            feed_count += 1

            # Check required fields
            if not meta.get("triggers", {}).get("keywords"):
                click.echo(f"  Warning: {child.name}/ META.yaml missing triggers.keywords")
                warnings += 1

            if not meta.get("fields"):
                click.echo(f"  Warning: {child.name}/ META.yaml missing fields")
                warnings += 1

            # Check for GUIDE.md
            if not (child / "GUIDE.md").exists():
                click.echo(f"  Warning: {child.name}/ missing GUIDE.md")
                warnings += 1

    click.echo(f"Feeds: {feed_count}")
    if warnings:
        click.echo(f"Warnings: {warnings}")
    else:
        click.echo("All checks passed")
