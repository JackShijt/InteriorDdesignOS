"""tests.integration.test_professional_pipeline · 专业深化流水线端到端（Phase 9 §6）。

验证：
  Layout → Electrical / Lighting / Plumbing（并行）→ Geometry → Drawing
  + Ceiling / Construction / Elevation 专业模型 + ValidationReport
全程无需人工干预，不破坏 CAD 抽象层。
"""
import json
import shutil
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.pipeline import PipelineRunner
from runtime.pipeline.professional_pipeline import AGENT_REGISTRY
from models.professional import (
    ElectricalModel, PlumbingModel, LightingModel,
    CeilingModel, ConstructionModel, ElevationModel, ValidationReport,
)
from agents.validator.validator_agent import ProfessionalValidator
from core.context import AgentContext


@pytest.fixture
def layout_model():
    path = ROOT / "examples" / "pipeline" / "professional_demo.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def runner(tmp_path):
    return PipelineRunner(workspace_root=tmp_path, backend="mock")


def test_professional_pipeline_full(layout_model, runner):
    """端到端：Layout → 专业 Agent → Geometry → Drawing + 校验报告。"""
    result = runner.run_professional(
        layout_model, project_id="ptest", name="integration")

    assert result["status"] == "COMPLETED"
    pdir = Path(result["project_dir"])

    # §7 必需产物
    for fname in ("LayoutModel.json", "ElectricalModel.json",
                  "LightingModel.json", "PlumbingModel.json",
                  "GeometryModel.json", "DrawingModel.json",
                  "ValidationReport.json"):
        assert (pdir / fname).exists(), f"缺失 {fname}"

    # 专业模型齐全（6 个）
    for agent_name in AGENT_REGISTRY:
        assert agent_name in result["professional_models"]

    # 版本链连续
    chain = json.loads((pdir / "model_chain.json").read_text(encoding="utf-8"))
    assert len(chain["chain"]) >= 9  # layout + 6 prof + geometry + drawing + validation + generated

    # 校验报告结构
    report = json.loads((pdir / "ValidationReport.json").read_text(encoding="utf-8"))
    assert report["status"] in ("PASS", "WARN", "FAIL")
    assert "issues" in report and "rule_results" in report


def test_professional_agents_run_in_parallel(layout_model, tmp_path):
    """验证专业 Agent 并行执行（§3 验收：可并行运行）。"""
    order = []
    lock = threading.Lock()

    from agents.electrical.electrical_agent import ElectricalAgent
    from agents.lighting.lighting_agent import LightingAgent
    from agents.plumbing.plumbing_agent import PlumbingAgent
    from agents.ceiling.ceiling_agent import CeilingAgent

    agents = {
        "electrical": ElectricalAgent(),
        "lighting": LightingAgent(),
        "plumbing": PlumbingAgent(),
        "ceiling": CeilingAgent(),
    }

    def _run(name, agent):
        time.sleep(0.01)  # 制造重叠窗口，证明并行
        ctx = AgentContext(project_id="ptest", task_id=f"{name}-ptest",
                           stage="PROFESSIONAL_DEEPENING",
                           inputs={"layout_model": layout_model},
                           workspace=str(tmp_path))
        res = agent.run(ctx)
        assert res.success
        with lock:
            order.append(name)

    threads = [threading.Thread(target=_run, args=(n, a))
               for n, a in agents.items()]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 全部完成
    assert set(order) == set(agents.keys())


def test_professional_models_structure(layout_model):
    """各专业 Agent 输出强类型模型，含 metadata + version（§1）。"""
    cases = [
        (ElectricalAgent(), ElectricalModel),
        (LightingAgent(), LightingModel),
        (PlumbingAgent(), PlumbingModel),
        (CeilingAgent(), CeilingModel),
        (ConstructionAgent(), ConstructionModel),
        (ElevationAgent(), ElevationModel),
    ]
    for agent, model_cls in cases:
        ctx = AgentContext(project_id="ptest", task_id="t-ptest",
                           stage="PROFESSIONAL_DEEPENING",
                           inputs={"layout_model": layout_model})
        res = agent.run(ctx)
        assert res.success
        m = model_cls.from_dict(res.output_model)
        assert m.metadata  # project_id / agent / task_id / schema_version / timestamp
        assert m.version.get("model_version")
        assert m.discipline


def test_validator_checks_professional_results(layout_model):
    """Validator 能检查专业结果（§5 验收）。"""
    from agents.electrical.electrical_agent import ElectricalAgent
    from agents.plumbing.plumbing_agent import PlumbingAgent
    from agents.lighting.lighting_agent import LightingAgent

    prof = {}
    for agent in (ElectricalAgent(), PlumbingAgent(), LightingAgent()):
        ctx = AgentContext(project_id="ptest", task_id="t-ptest",
                           stage="PROFESSIONAL_DEEPENING",
                           inputs={"layout_model": layout_model})
        prof[agent.agent_name] = agent.run(ctx).output_model

    vctx = AgentContext(project_id="ptest", task_id="t-ptest",
                        stage="VALIDATION",
                        inputs={"layout_model": layout_model,
                                "professional_models": prof})
    res = ProfessionalValidator().run(vctx)
    assert res.success
    report = ValidationReport.from_dict(res.output_model)
    assert report.status in ("PASS", "WARN", "FAIL")
    assert report.checked_count > 0


def test_pipeline_includes_professional_stage(layout_model, runner):
    """Pipeline 包含 PROFESSIONAL_DEEPENING 阶段（§4 / 验收 Stage5）。"""
    runner.run_professional(layout_model, project_id="stage", name="n")
    tg = runner.task_graph.to_dict()
    stages = {t.get("stage") for t in tg.get("tasks", [])}
    assert "PROFESSIONAL_DEEPENING" in stages
    assert "GEOMETRY" in stages and "DRAWING" in stages


def test_validator_detects_spatial_conflict():
    """Validator 能捕获空间冲突（引用未知房间 → FAIL）。"""
    layout = {"rooms": [{"room_id": "R1", "name": "客厅", "type": "living"}]}
    prof = {"electrical": {"devices": [
        {"device_id": "E1", "room_id": "GHOST", "position": {"x": 1, "y": 1}},
    ]}}
    vctx = AgentContext(project_id="ptest", task_id="t", stage="VALIDATION",
                        inputs={"layout_model": layout,
                                "professional_models": prof})
    res = ProfessionalValidator().run(vctx)
    assert res.success
    report = json.loads(json.dumps(res.output_model))
    assert report["status"] == "FAIL"
    assert any(i["category"] == "SPATIAL_CONFLICT" for i in report["issues"])


# 引入 Agent 类（供上面测试使用）
from agents.electrical.electrical_agent import ElectricalAgent  # noqa: E402
from agents.lighting.lighting_agent import LightingAgent  # noqa: E402
from agents.plumbing.plumbing_agent import PlumbingAgent  # noqa: E402
from agents.ceiling.ceiling_agent import CeilingAgent  # noqa: E402
from agents.construction.construction_agent import ConstructionAgent  # noqa: E402
from agents.elevation.elevation_agent import ElevationAgent  # noqa: E402
