"""
Phase 2 冒烟测试：验证 Orchestrator 框架可完整运行（不实现任何装修逻辑）。

运行：
  cd InteriorDesignOS && python3 -m pytest tests/test_orchestrator_smoke.py -q
或：
  cd InteriorDesignOS && python3 tests/test_orchestrator_smoke.py
"""

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.orchestrator import Orchestrator  # noqa: E402
from runtime.message import EventType  # noqa: E402


def _run_project(project_id: str, workspace_root: Path, log_dir: Path):
    orch = Orchestrator(project_id, workspace_root=workspace_root, log_dir=log_dir)
    return orch.run()


def test_full_run_completes():
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "workspace"
        logs = ws / "logs"
        summary = _run_project("p1", ws, logs)
        assert summary["status"] == "COMPLETED"
        assert summary["current_stage"] == "EXPORT"
        # 所有任务完成
        assert all(s == "COMPLETED" for s in summary["tasks"].values())
        # 检查点已保存（project + 模型快照）
        assert "project.json" in summary["checkpoints"]
        assert any(c.startswith("layout_v") for c in summary["checkpoints"])
        assert any(c.startswith("geometry_v") for c in summary["checkpoints"])


def test_events_published():
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "workspace"
        logs = ws / "logs"
        orch = Orchestrator("p2", workspace_root=ws, log_dir=logs)
        orch.run()
        types = {ev["type"] for ev in orch.events}
        for required in (EventType.TASK_CREATED.value, EventType.TASK_STARTED.value,
                         EventType.TASK_FINISHED.value, EventType.STAGE_CHANGED.value,
                         EventType.PROJECT_FINISHED.value):
            assert required in types, f"缺少事件: {required}"


def test_recovery_skips_completed():
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "workspace"
        logs = ws / "logs"
        # 第一次完整运行
        _run_project("p3", ws, logs)
        # 第二次运行同一 project_id -> 恢复，应仍 COMPLETED
        summary = _run_project("p3", ws, logs)
        assert summary["status"] == "COMPLETED"
        assert all(s == "COMPLETED" for s in summary["tasks"].values())


def test_failure_does_not_crash():
    from agents.orchestrator import AgentRegistry, StubAgent
    from agents.orchestrator.agent import Result, AgentContext

    class FailAgent(StubAgent):
        def run(self, context: AgentContext) -> Result:
            return Result(success=False, messages=["boom"])

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "workspace"
        logs = ws / "logs"
        reg = AgentRegistry()
        for s in ["INITIALIZATION", "INPUT_ANALYSIS", "ORIGINAL_MODEL", "DESIGN_SPEC",
                  "LAYOUT", "PROFESSIONAL_DEEPENING", "GEOMETRY", "DRAWING",
                  "DWG_GENERATION", "VALIDATION", "REPAIR", "EXPORT"]:
            reg.register(FailAgent(agent_name=s.lower()) if s == "DRAWING"
                         else StubAgent(agent_name=s.lower()))
        orch = Orchestrator("p4", registry=reg, workspace_root=ws, log_dir=logs)
        summary = orch.run()
        assert summary["status"] == "FAILED"
        assert summary["tasks"].get("drawing-p4") == "FAILED"


if __name__ == "__main__":
    test_full_run_completes()
    test_events_published()
    test_recovery_skips_completed()
    test_failure_does_not_crash()
    print("ALL PHASE 2 SMOKE TESTS PASSED")
