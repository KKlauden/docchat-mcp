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
    """目标目录无 docchat.yaml 时自动创建"""
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
