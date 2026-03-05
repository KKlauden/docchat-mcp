"""Knowledge pack configuration schema."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Dimension:
    """A single classification dimension (e.g. product, sport, region)."""

    key: str
    label: str
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class AssistantConfig:
    """Optional assistant customization for MCP instructions and prompts."""

    name: str = "API Assistant"
    preamble_zh: str = "你是 API 技术支持助手。请基于以下文档信息回答用户的问题。"
    preamble_en: str = (
        "You are an API technical support assistant. "
        "Answer based on the documentation below."
    )


@dataclass
class PackConfig:
    """Root knowledge pack configuration (parsed from docchat.yaml)."""

    name: str
    display_name: str = ""
    version: str = "0.1.0"
    description: str = ""
    dimensions: list[Dimension] = field(default_factory=list)
    assistant: AssistantConfig = field(default_factory=AssistantConfig)

    def make_index_key(self, values: dict[str, str]) -> str:
        """Build composite index key from dimension values.

        E.g. {"product": "sdapi", "sport": "soccer"} -> "sdapi:soccer"
        Zero dimensions -> ""
        """
        parts = [values.get(d.key, "") for d in self.dimensions]
        return ":".join(p for p in parts if p)


def load_pack_config(pack_dir: Path) -> PackConfig:
    """Load and parse docchat.yaml from a knowledge pack directory."""
    config_path = pack_dir / "docchat.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"No docchat.yaml found in {pack_dir}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    dims = []
    for d in raw.get("dimensions") or []:
        dims.append(
            Dimension(
                key=d["key"],
                label=d.get("label", d["key"]),
                values=d.get("values", {}),
            )
        )

    asst_raw = raw.get("assistant") or {}
    assistant = AssistantConfig(
        name=asst_raw.get("name", AssistantConfig.name),
        preamble_zh=asst_raw.get("preamble_zh", AssistantConfig.preamble_zh),
        preamble_en=asst_raw.get("preamble_en", AssistantConfig.preamble_en),
    )

    return PackConfig(
        name=raw["name"],
        display_name=raw.get("display_name", raw["name"]),
        version=raw.get("version", "0.1.0"),
        description=raw.get("description", ""),
        dimensions=dims,
        assistant=assistant,
    )
