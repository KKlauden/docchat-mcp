"""Tests for knowledge pack configuration schema."""

import pytest
from docchat.schema import load_pack_config, PackConfig, Dimension


def test_load_minimal_config(tmp_path):
    """最简配置：只有 name。"""
    (tmp_path / "docchat.yaml").write_text("name: my-api\n")
    config = load_pack_config(tmp_path)
    assert config.name == "my-api"
    assert config.dimensions == []


def test_load_config_with_dimensions(tmp_path):
    """带自定义层级的配置。"""
    (tmp_path / "docchat.yaml").write_text(
        "name: opta-sports\n"
        'display_name: "Opta Sports API"\n'
        "dimensions:\n"
        "  - key: product\n"
        '    label: "Product"\n'
        "    values:\n"
        '      sdapi: "SDAPI"\n'
        '      sddp: "SDDP"\n'
        "  - key: sport\n"
        '    label: "Sport"\n'
        "    values:\n"
        '      soccer: "Soccer"\n'
        '      basketball: "Basketball"\n'
    )
    config = load_pack_config(tmp_path)
    assert len(config.dimensions) == 2
    assert config.dimensions[0].key == "product"
    assert "sdapi" in config.dimensions[0].values


def test_load_config_zero_dimensions(tmp_path):
    """零层级：所有 feed 平铺。"""
    (tmp_path / "docchat.yaml").write_text("name: simple-api\ndimensions: []\n")
    config = load_pack_config(tmp_path)
    assert config.dimensions == []


def test_missing_config_raises(tmp_path):
    """缺少 docchat.yaml 时报错。"""
    with pytest.raises(FileNotFoundError):
        load_pack_config(tmp_path)


def test_make_index_key_no_dimensions():
    """零维度时索引键为空字符串。"""
    config = PackConfig(name="test", dimensions=[])
    assert config.make_index_key({}) == ""


def test_make_index_key_two_dimensions():
    """两层维度时索引键为 'val1:val2'。"""
    config = PackConfig(
        name="test",
        dimensions=[
            Dimension(key="product", label="P", values={"sdapi": "SDAPI"}),
            Dimension(key="sport", label="S", values={"soccer": "Soccer"}),
        ],
    )
    assert config.make_index_key({"product": "sdapi", "sport": "soccer"}) == "sdapi:soccer"


def test_load_config_with_assistant(tmp_path):
    """带 assistant 配置。"""
    (tmp_path / "docchat.yaml").write_text(
        "name: test\n"
        "assistant:\n"
        '  name: "My Assistant"\n'
        '  preamble_en: "You are the Stripe API assistant."\n'
    )
    config = load_pack_config(tmp_path)
    assert config.assistant.name == "My Assistant"
    assert "Stripe" in config.assistant.preamble_en
