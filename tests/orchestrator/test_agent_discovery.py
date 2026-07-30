"""Phase 10 §8 · Agent 自动发现测试。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.agent_registry import AgentCapabilityRegistry  # noqa: E402


def _registry() -> AgentCapabilityRegistry:
    return AgentCapabilityRegistry()


def test_scan_discovers_agents_from_contracts():
    reg = _registry()
    names = set(reg.names())
    # 关键 Agent 必须被扫描到（来自 agent_contract.json，非硬编码）
    for expected in ("layout", "geometry", "drawing", "validator",
                     "electrical", "lighting", "plumbing", "ceiling"):
        assert expected in names, f"未发现 {expected}"
    assert not reg.errors, f"契约解析错误: {reg.errors}"


def test_contract_fields_normalized():
    reg = _registry()
    electrical = reg.get("electrical")
    assert electrical is not None
    assert electrical.agent_name == "electrical"
    assert "LayoutModel" in electrical.input_schema
    assert "ElectricalModel" in electrical.output_schema
    assert "professional_deepening" in electrical.capabilities
    # forbidden_actions 兼容历史 forbidden 字段
    assert electrical.forbidden_actions
    # 历史契约（validator）使用 forbidden 字段，也应被归一化
    validator = reg.get("validator")
    assert validator.forbidden_actions


def test_find_agent_by_input_output_capability():
    reg = _registry()
    # 消费 LayoutModel 的 Agent（geometry + 专业 Agent）
    consumers = {c.agent_name for c in reg.find_agent_by_input("LayoutModel")}
    assert {"geometry", "electrical", "lighting"} <= consumers
    # 产出 GeometryModel 的 Agent
    producers = {c.agent_name for c in reg.find_agent_by_output("GeometryModel")}
    assert producers == {"geometry"}
    # 具备 professional_deepening 能力的 Agent
    prof = {c.agent_name for c in reg.find_agent_by_capability("professional_deepening")}
    assert {"electrical", "lighting", "plumbing", "ceiling"} <= prof


def test_no_hardcoded_agents_uses_directory_scan(tmp_path):
    # 指向空目录时应发现 0 个 Agent，证明来源为目录扫描而非硬编码
    empty = AgentCapabilityRegistry(agents_dir=tmp_path)
    assert empty.list_agents() == []
