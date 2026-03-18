"""DocChat CLI — init / import / build / validate / serve / mcp / connect."""

from pathlib import Path

import click
import yaml


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _get_bundled_skill(filename: str) -> str:
    """Return the content of a bundled skill file from package data."""
    from importlib.resources import files

    data_file = files("docchat") / "data" / filename
    return data_file.read_text(encoding="utf-8")


def _install_skill_files(target: Path) -> None:
    """Generate AUTHORING.md + .claude/skills/ skill files under *target*."""
    author_content = _get_bundled_skill("docchat-author.md")
    reviewer_content = _get_bundled_skill("docchat-reviewer.md")

    # AUTHORING.md — tool-agnostic, at project root
    (target / "AUTHORING.md").write_text(author_content, encoding="utf-8")

    # .claude/skills/ — Claude Code auto-discovers as slash commands
    claude_skills_dir = target / ".claude" / "skills"
    claude_skills_dir.mkdir(parents=True, exist_ok=True)
    (claude_skills_dir / "docchat-author.md").write_text(author_content, encoding="utf-8")
    (claude_skills_dir / "docchat-reviewer.md").write_text(reviewer_content, encoding="utf-8")


def _init_pack(target: Path, name: str) -> None:
    """Create docchat.yaml + feeds/ + _shared/ + _overview/ + skill files under *target*."""
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

    # Skill files for AI-assisted authoring
    _install_skill_files(target)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def main():
    """DocChat - Turn API docs into an intelligent MCP server."""
    pass


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@main.command()
@click.option("--dir", "target_dir", default=".", help="Target directory")
@click.option("--name", prompt="Knowledge pack name", help="Knowledge pack name")
def init(target_dir: str, name: str):
    """Initialize a knowledge pack (docchat.yaml + directory structure)."""
    target = Path(target_dir)
    _init_pack(target, name)

    feeds_dir = target / "feeds"
    click.echo(f"Initialized knowledge pack '{name}' in {target.resolve()}")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. In Claude Code: /docchat-author or ask AI to help write the docs")
    click.echo("  2. Run: docchat validate")
    click.echo("  3. Run: docchat connect")


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------


@main.command(name="import")
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--dir", "target_dir", default=".", help="Target knowledge pack directory")
@click.option(
    "--group",
    type=click.Choice(["endpoint", "resource"]),
    default=None,
    help="Feed grouping granularity",
)
@click.option("--yes", is_flag=True, help="Non-interactive mode, skip existing feeds")
def import_cmd(spec_file: str, target_dir: str, group: str | None, yes: bool):
    """Import feeds from an OpenAPI / Swagger specification."""
    from rich.console import Console  # lazy import

    console = Console()

    # 1. 解析 spec
    from docchat.importers.openapi import OpenAPIImporter  # lazy import

    try:
        importer = OpenAPIImporter(spec_file).parse()
    except Exception as exc:
        console.print(f"[red]Error parsing spec:[/red] {exc}")
        raise SystemExit(1)

    # 2. 显示解析结果
    console.print(
        f"[green]Parsed spec:[/green] {importer.endpoint_count} endpoints, "
        f"{importer.resource_count} resources"
    )

    # 3. 确定分组方式
    if group is not None:
        grouping = group
    elif yes:
        grouping = "endpoint"
    else:
        import questionary  # lazy import

        grouping = questionary.select(
            "Feed grouping granularity:",
            choices=["endpoint", "resource"],
            default="endpoint",
        ).ask()
        if grouping is None:
            raise SystemExit(0)

    # 4. 确定目标目录
    if target_dir != ".":
        target = Path(target_dir)
    elif yes:
        target = Path(target_dir)
    else:
        import questionary  # lazy import

        chosen = questionary.path(
            "Target knowledge pack directory:",
            default=target_dir,
        ).ask()
        if chosen is None:
            raise SystemExit(0)
        target = Path(chosen)

    # 5. 检查 docchat.yaml 是否存在
    config_path = target / "docchat.yaml"
    if not config_path.exists():
        if yes:
            pack_name = target.resolve().name
            _init_pack(target, pack_name)
            console.print(f"[green]Initialized knowledge pack '{pack_name}' in {target.resolve()}[/green]")
        else:
            import questionary  # lazy import

            create = questionary.confirm(
                f"No docchat.yaml found in {target.resolve()}. Create a new knowledge pack?",
                default=True,
            ).ask()
            if not create:
                console.print("[yellow]Aborted.[/yellow]")
                raise SystemExit(0)
            pack_name = questionary.text(
                "Knowledge pack name:",
                default=target.resolve().name,
            ).ask()
            if pack_name is None:
                raise SystemExit(0)
            _init_pack(target, pack_name)
            console.print(f"[green]Initialized knowledge pack '{pack_name}' in {target.resolve()}[/green]")
    # else: docchat.yaml 存在，继续

    # 6. feeds 目录
    feeds_dir = target / "feeds"
    feeds_dir.mkdir(parents=True, exist_ok=True)

    # 7. 生成 FeedSkeleton 列表
    if grouping == "endpoint":
        feeds = importer.group_by_endpoint()
    else:
        feeds = importer.group_by_resource()

    # 8. 冲突处理回调
    if yes:
        def on_conflict(feed_code: str) -> str:
            return "skip"
    else:
        import questionary  # lazy import

        def on_conflict(feed_code: str) -> str:
            overwrite = questionary.confirm(
                f"Feed '{feed_code}' already exists. Overwrite?",
                default=False,
            ).ask()
            return "overwrite" if overwrite else "skip"

    # 9. 生成文件
    gen_result = importer.generate(feeds, feeds_dir, on_conflict)

    # 10. 输出结果
    for code in gen_result.created:
        console.print(f"  [green]✓[/green] created   {code}")
    for code in gen_result.skipped:
        console.print(f"  [yellow]⊘[/yellow] skipped   {code}")
    for code in gen_result.overwritten:
        console.print(f"  [blue]↻[/blue] overwritten {code}")

    total = len(gen_result.created) + len(gen_result.skipped) + len(gen_result.overwritten)
    console.print(
        f"\n[bold]Done:[/bold] {len(gen_result.created)} created, "
        f"{len(gen_result.skipped)} skipped, "
        f"{len(gen_result.overwritten)} overwritten "
        f"(total {total} feeds)"
    )

    # Next steps
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  [bold cyan]AI-assisted (recommended):[/bold cyan]")
    console.print("    In Claude Code: /docchat-author or ask AI to improve the docs")
    console.print("    In other tools: tell AI to read AUTHORING.md and improve the docs")
    console.print()
    console.print("  [bold cyan]Connect to Claude Code:[/bold cyan]")
    console.print("    docchat connect")
    console.print()
    console.print("  [dim]Manual:[/dim]")
    console.print("    1. Fill in triggers.keywords in each feed's META.yaml")
    console.print("    2. Complete GUIDE.md with accurate documentation")
    console.print("    3. Run: docchat validate")
    console.print("    4. Run: docchat build")
    console.print("    5. docchat connect  (or: docchat serve)")


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


@main.command()
@click.option("--dir", "pack_dir", default=".", help="Knowledge pack directory")
@click.option("--port", default=8710, help="HTTP port")
def serve(pack_dir: str, port: int):
    """Start MCP Server (HTTP mode)."""
    from docchat.mcp_server import create_mcp_server

    target = Path(pack_dir)
    mcp = create_mcp_server(target)
    click.echo(f"Starting MCP server on port {port}...")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)


# ---------------------------------------------------------------------------
# mcp
# ---------------------------------------------------------------------------


@main.command("mcp")
@click.option("--dir", "pack_dir", default=".", help="Knowledge pack directory")
def mcp_stdio(pack_dir: str):
    """Start MCP Server (stdio mode, for Claude Code)."""
    from docchat.mcp_server import create_mcp_server

    target = Path(pack_dir)
    mcp = create_mcp_server(target)
    mcp.run(transport="stdio")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# connect
# ---------------------------------------------------------------------------


@main.command()
@click.option("--dir", "pack_dir", default=".", help="Knowledge pack directory")
def connect(pack_dir: str):
    """Register this knowledge pack as a Claude Code MCP server."""
    import shutil
    import subprocess

    target = Path(pack_dir).resolve()

    # Check docchat.yaml exists
    config_path = target / "docchat.yaml"
    if not config_path.exists():
        click.echo(f"Error: No docchat.yaml found in {target}", err=True)
        raise SystemExit(1)

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    name = config.get("name", target.name)

    # Check claude CLI is available
    if not shutil.which("claude"):
        click.echo("Error: 'claude' CLI not found. Install Claude Code first.", err=True)
        raise SystemExit(1)

    # Register MCP server
    cmd = [
        "claude", "mcp", "add", name, "--",
        "uvx", "--from", "docchat-mcp", "docchat", "mcp", "--dir", str(target),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        click.echo(f"Error: {result.stderr.strip()}", err=True)
        raise SystemExit(1)

    click.echo(f"Connected '{name}' to Claude Code.")
    click.echo(f"Restart Claude Code in {target} to start using it.")
    click.echo()
    click.echo("For other AI tools, start the HTTP server instead:")
    click.echo(f"  docchat serve --dir {target}")
