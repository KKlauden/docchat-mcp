"""Tests for CLI tool."""

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
