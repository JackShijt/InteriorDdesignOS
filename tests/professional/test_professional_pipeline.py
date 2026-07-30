"""Professional Stage 端到端测试（Phase 5 §7/§8/§10/§11）。

Mock Workflow：LayoutModel → Parallel(Electrical/Lighting/HVAC/Furniture)
→ Validator（聚合）→ Export。
"""
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.orchestrator.agent import AgentContext, Result
from runtime.agent_registry import build_runtime_registry
from runtime.config import load_runtime_config
from runtime.pipeline import Pipeline
from professional.electrical.electrical_agent import ElectricalAgent

LAYOUT_EXAMPLE = REPO_ROOT / "schemas" / "examples" / "LayoutModel.example.json"
DEMO = ["electrical", "lighting", "hvac", "furniture"]


def _cfg():
    tmp = tempfile.mkdtemp()
    cfg = load_runtime_config()
    cfg["workspace_root"] = str(Path(tmp) / "workspace")
    cfg["workspace_path"] = str(Path(tmp) / "workspace")
    cfg["log_dir"] = str(Path(tmp) / "logs")
    return cfg


def test_mock_workflow_completes():
    cfg = _cfg()
    p = Pipeline("prof_demo", config=cfg)
    summary = p.run_professional(layout_path=str(LAYOUT_EXAMPLE),
                                 disciplines=DEMO)
    assert summary["status"] == "COMPLETED"
    assert summary["current_stage"] == "PROFESSIONAL_DEEPENING"
    for d in DEMO:
        assert summary["tasks"][f"professional-{d}-prof_demo"] == "COMPLETED"
    assert summary["professional"]["validation_passed"] is True

    proj_dir = Path(cfg["workspace_path"]) / "projects" / "prof_demo"
    for d in DEMO:
        model_file = proj_dir / "professional" / f"{d}_model.json"
        assert model_file.exists()
        model = json.loads(model_file.read_text(encoding="utf-8"))
        assert model["layout_model_version"] == "v1"
    report = json.loads((proj_dir / "professional_validation_report.json")
                        .read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["checked"] == len(DEMO)
    manifest = json.loads((proj_dir / "professional_export_manifest.json")
                          .read_text(encoding="utf-8"))
    assert len(manifest["models"]) == len(DEMO)
    assert (proj_dir / "checkpoint_professional_v1.json").exists()


def test_all_eight_disciplines_run_in_parallel_stage():
    cfg = _cfg()
    p = Pipeline("prof_all8", config=cfg)
    summary = p.run_professional(layout_path=str(LAYOUT_EXAMPLE))
    assert summary["status"] == "COMPLETED"
    prof_dir = (Path(cfg["workspace_path"]) / "projects" / "prof_all8"
                / "professional")
    assert len(list(prof_dir.glob("*_model.json"))) == 8


class _FlakyElectricalAgent(ElectricalAgent):
    """首次失败、重跑成功：验证只重跑失败 Agent（Phase 5 §8）。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = 0

    def run(self, context: AgentContext) -> Result:
        self.calls += 1
        if self.calls == 1:
            return Result(success=False, messages=["模拟首跑失败"])
        return super().run(context)


class _CountingAgent(ElectricalAgent):
    discipline = "lighting"  # 顶替 lighting，统计执行次数

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = 0

    def run(self, context: AgentContext) -> Result:
        self.calls += 1
        return super().run(context)


def test_partial_failure_retries_only_failed_agent():
    cfg = _cfg()
    registry = build_runtime_registry(
        workspace_root=Path(cfg["workspace_root"]),
        log_dir=Path(cfg["log_dir"]))
    flaky = _FlakyElectricalAgent(workspace_root=Path(cfg["workspace_root"]),
                                  log_dir=Path(cfg["log_dir"]))
    counting = _CountingAgent(workspace_root=Path(cfg["workspace_root"]),
                              log_dir=Path(cfg["log_dir"]))
    registry.register(flaky)
    registry.register(counting)

    p = Pipeline("prof_retry", config=cfg, registry=registry)
    summary = p.run_professional(layout_path=str(LAYOUT_EXAMPLE),
                                 disciplines=["electrical", "lighting"])
    assert summary["status"] == "COMPLETED"
    assert flaky.calls == 2, "失败 Agent 应被单独重跑一次"
    assert counting.calls == 1, "成功 Agent 不得被重新执行"
    assert summary["tasks"]["professional-electrical-prof_retry"] == "COMPLETED"
    assert summary["tasks"]["professional-lighting-prof_retry"] == "COMPLETED"
