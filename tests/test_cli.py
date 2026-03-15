"""Tests for CLI tool."""

import json

import yaml
from click.testing import CliRunner

from docchat.cli import main


def test_init_creates_config(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--dir", str(tmp_path), "--name", "test-api"])
    assert result.exit_code == 0
    assert (tmp_path / "docchat.yaml").exists()
    assert (tmp_path / "feeds").is_dir()


def test_init_creates_shared_and_overview(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--dir", str(tmp_path), "--name", "test-api"])
    assert result.exit_code == 0
    assert (tmp_path / "_shared" / "INDEX.yaml").exists()
    assert (tmp_path / "_overview" / "INDEX.md").exists()


def test_init_creates_skill_files(tmp_path):
    """init creates AUTHORING.md and .claude/skills/docchat-author.md."""
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--dir", str(tmp_path), "--name", "test-api"])
    assert result.exit_code == 0

    # AUTHORING.md at project root
    authoring = tmp_path / "AUTHORING.md"
    assert authoring.exists()
    content = authoring.read_text(encoding="utf-8")
    assert "DocChat Author" in content
    assert "docchat-author" in content

    # .claude/skills/docchat-author.md for Claude Code
    claude_skill = tmp_path / ".claude" / "skills" / "docchat-author.md"
    assert claude_skill.exists()
    assert claude_skill.read_text(encoding="utf-8") == content


def test_init_config_content(tmp_path):
    runner = CliRunner()
    runner.invoke(main, ["init", "--dir", str(tmp_path), "--name", "my-cool-api"])
    config = yaml.safe_load((tmp_path / "docchat.yaml").read_text())
    assert config["name"] == "my-cool-api"


def test_validate_minimal_pack(tmp_path):
    # Create a minimal valid pack
    (tmp_path / "docchat.yaml").write_text("name: test\n")
    (tmp_path / "feeds").mkdir()
    feed_dir = tmp_path / "feeds" / "get-users"
    feed_dir.mkdir()
    (feed_dir / "META.yaml").write_text(
        "name: get-users\n"
        "feed_name: Get Users\n"
        "triggers:\n"
        "  keywords:\n"
        "    - users\n"
        "fields:\n"
        "  - userId\n"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--dir", str(tmp_path)])
    assert result.exit_code == 0


def test_validate_missing_config(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--dir", str(tmp_path)])
    assert result.exit_code != 0


def test_validate_missing_triggers(tmp_path):
    (tmp_path / "docchat.yaml").write_text("name: test\n")
    feed_dir = tmp_path / "feeds" / "bad-feed"
    feed_dir.mkdir(parents=True)
    (feed_dir / "META.yaml").write_text("name: bad-feed\nfeed_name: Bad\n")
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--dir", str(tmp_path)])
    # Should warn but not crash
    assert result.exit_code == 0
    assert "warning" in result.output.lower() or "missing" in result.output.lower()


def test_build(tmp_path):
    (tmp_path / "docchat.yaml").write_text("name: test\n")
    feed_dir = tmp_path / "feeds" / "get-users"
    feed_dir.mkdir(parents=True)
    (feed_dir / "META.yaml").write_text(
        "name: get-users\n"
        "feed_name: Get Users\n"
        "triggers:\n"
        "  keywords:\n"
        "    - users\n"
        "fields:\n"
        "  - userId\n"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["build", "--dir", str(tmp_path)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# import tests
# ---------------------------------------------------------------------------

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
    """非交互模式导入"""
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
    assert result.exit_code == 0, result.output
    assert (target / "feeds" / "list-items" / "META.yaml").exists()
    assert (target / "feeds" / "list-items" / "GUIDE.md").exists()


def test_import_creates_pack_if_missing(tmp_path):
    """目标目录无 docchat.yaml 时自动创建（含 skill 文件）"""
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(TINY_SPEC))

    target = tmp_path / "new-pack"

    runner = CliRunner()
    result = runner.invoke(
        main, ["import", str(spec_path), "--dir", str(target), "--yes", "--group", "endpoint"]
    )
    assert result.exit_code == 0, result.output
    assert (target / "docchat.yaml").exists()
    assert (target / "feeds" / "list-items" / "META.yaml").exists()
    # Skill files should be created when pack is initialized
    assert (target / "AUTHORING.md").exists()
    assert (target / ".claude" / "skills" / "docchat-author.md").exists()


def test_import_skip_existing(tmp_path):
    """--yes 模式跳过已存在的 feed"""
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
    assert result.exit_code == 0, result.output
    content = (feeds_dir / "list-items" / "META.yaml").read_text()
    assert "existing: true" in content


# ---------------------------------------------------------------------------
# connect tests
# ---------------------------------------------------------------------------


def test_connect_missing_config(tmp_path):
    """docchat.yaml 不存在时报错"""
    runner = CliRunner()
    result = runner.invoke(main, ["connect", "--dir", str(tmp_path)])
    assert result.exit_code != 0
    assert "No docchat.yaml found" in result.output or "No docchat.yaml found" in (result.stderr or "")


def test_connect_missing_claude_cli(tmp_path, monkeypatch):
    """claude CLI 不存在时报错"""
    (tmp_path / "docchat.yaml").write_text("name: test-api\n")

    # 确保 shutil.which("claude") 返回 None
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    runner = CliRunner()
    result = runner.invoke(main, ["connect", "--dir", str(tmp_path)])
    assert result.exit_code != 0
