"""BaseProfessionalAgent / 8 个专业 Agent 单元测试（Phase 5 §11）。"""
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.orchestrator.agent import AgentContext
from professional import PROFESSIONAL_DISCIPLINES, build_professional_agents
from professional.base.professional_agent import (BaseProfessionalAgent,
                                                  ProfessionalInputError)
from professional.electrical.electrical_agent import ElectricalAgent

LAYOUT_EXAMPLE = REPO_ROOT / "schemas" / "examples" / "LayoutModel.example.json"


def _ctx(project_id: str, discipline: str, layout_path: Path) -> AgentContext:
    return AgentContext(project_id=project_id,
                        task_id=f"professional-{discipline}-{project_id}",
                        stage="PROFESSIONAL_DEEPENING",
                        parameters={"layout_path": str(layout_path)})


def _tmp_ws() -> Path:
    return Path(tempfile.mkdtemp()) / "workspace"


def test_electrical_agent_run_and_export():
    ws = _tmp_ws()
    agent = ElectricalAgent(workspace_root=ws)
    result = agent.run(_ctx("p1", "electrical", LAYOUT_EXAMPLE))
    assert result.success, result.messages
    model = result.output_model
    assert model["discipline"] == "ELECTRICAL"
    assert model["layout_model_version"] == "v1"
    assert model["objects"], "Mock 对象不应为空"
    assert model["quality"]["validation_passed"] is True
    out = ws / "projects" / "p1" / "professional" / "electrical_model.json"
    assert out.exists()
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["discipline"] == "ELECTRICAL"


def test_all_eight_agents_runnable():
    """DoD：8 个 Professional Agent 全部可运行（Mock）。"""
    ws = _tmp_ws()
    agents = build_professional_agents(workspace_root=ws)
    assert len(agents) == 8
    for agent in agents:
        result = agent.run(_ctx("p8", agent.discipline, LAYOUT_EXAMPLE))
        assert result.success, f"{agent.discipline}: {result.messages}"
        assert result.output_model["discipline"] in (
            "ELECTRICAL", "PLUMBING", "LIGHTING", "CEILING",
            "FLOORING", "HVAC", "CONSTRUCTION", "FURNITURE")
        out = (ws / "projects" / "p8" / "professional"
               / f"{agent.discipline}_model.json")
        assert out.exists()


def test_layout_is_readonly():
    """Agent 不允许修改 LayoutModel（SSOT）：源文件内容保持不变。"""
    ws = _tmp_ws()
    tmp_layout = ws / "layout_copy.json"
    tmp_layout.parent.mkdir(parents=True, exist_ok=True)
    original_text = LAYOUT_EXAMPLE.read_text(encoding="utf-8")
    tmp_layout.write_text(original_text, encoding="utf-8")

    for agent in build_professional_agents(workspace_root=ws):
        result = agent.run(_ctx("ro", agent.discipline, tmp_layout))
        assert result.success
    assert tmp_layout.read_text(encoding="utf-8") == original_text


def test_validate_input_rejects_bad_layout():
    agent = ElectricalAgent(workspace_root=_tmp_ws())
    try:
        agent.validate_input({"rooms": []})
        raise AssertionError("应当抛出 ProfessionalInputError")
    except ProfessionalInputError:
        pass
    try:
        agent.validate_input({"metadata": {}, "version": {}, "rooms": [],
                              "walls": []})
        raise AssertionError("缺 model_version 应当抛出")
    except ProfessionalInputError:
        pass


def test_missing_layout_returns_failed_result():
    """框架安全：缺输入不抛异常，返回失败 Result。"""
    agent = ElectricalAgent(workspace_root=_tmp_ws())
    ctx = AgentContext(project_id="nolayout", task_id="t1",
                       stage="PROFESSIONAL_DEEPENING")
    result = agent.run(ctx)
    assert result.success is False
    assert result.messages


def test_base_agent_common_logic_not_duplicated():
    """所有专业 Agent 必须继承 BaseProfessionalAgent（Phase 5 §3）。"""
    for agent in build_professional_agents(workspace_root=_tmp_ws()):
        assert isinstance(agent, BaseProfessionalAgent)
        # 公共逻辑由基类提供（子类不得覆写）
        for method in ("run", "load_layout", "load_design_spec",
                       "validate_input", "generate_model", "export_model",
                       "quality_check"):
            assert getattr(type(agent), method) is getattr(
                BaseProfessionalAgent, method), (
                f"{agent.discipline}.{method} 不应重复实现公共逻辑")
    assert set(PROFESSIONAL_DISCIPLINES) == {
        "electrical", "plumbing", "lighting", "ceiling",
        "flooring", "hvac", "construction", "furniture"}
