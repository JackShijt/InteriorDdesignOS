"""Phase 10 §8/§9 · 动态编排流水线端到端测试。

验收：输入一个项目需求，系统自动 建项 → 分析 → 生成 TaskGraph →
找到 Agent → 执行任务 → 保存 Checkpoint（不再人工指定调用顺序）。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.pipeline import PipelineRunner  # noqa: E402
from runtime.pipeline.orchestrated_pipeline import OrchestratedPipeline  # noqa: E402
from runtime.orchestrator.task_planner import ProjectRequirement  # noqa: E402


def _layout():
    demo = ROOT / "examples" / "pipeline" / "professional_demo.json"
    return json.loads(demo.read_text(encoding="utf-8"))


def _requirement(project_id="p-e2e"):
    return ProjectRequirement(
        project_id=project_id,
        name="orchestrated-test",
        initial_schemas=["DesignSpec"],
        target_schemas=["DrawingModel", "ValidationReport"],
        disciplines=["electrical", "lighting", "plumbing", "ceiling"],
        inputs={"layout_model": _layout()},
    )


def test_end_to_end_completes(tmp_path):
    op = OrchestratedPipeline(workspace_root=tmp_path, backend="mock")
    result = op.run(_requirement())
    assert result["status"] == "COMPLETED"
    # 全部任务完成
    assert set(result["tasks"].values()) == {"COMPLETED"}
    # 自动生成的执行顺序覆盖 layout -> professional -> geometry -> drawing -> validator
    plan = result["plan"]
    assert "layout_task" in plan and "validator_task" in plan
    assert result["validation_status"] is not None
    assert result["command_count"] > 0


def test_checkpoints_and_artifacts_saved(tmp_path):
    op = OrchestratedPipeline(workspace_root=tmp_path, backend="mock")
    result = op.run(_requirement("p-artifacts"))
    pdir = Path(result["project_dir"])
    for fname in ("orchestration_plan.json", "task_graph.json",
                  "model_chain.json", "LayoutModel.json", "GeometryModel.json",
                  "DrawingModel.json", "ValidationReport.json",
                  "ConflictReport.json"):
        assert (pdir / fname).exists(), f"缺少产物 {fname}"


def test_professional_models_produced(tmp_path):
    op = OrchestratedPipeline(workspace_root=tmp_path, backend="mock")
    result = op.run(_requirement("p-prof"))
    assert {"ELECTRICAL", "LIGHTING", "PLUMBING", "CEILING"} <= set(
        result["professional_models"])
    pdir = Path(result["project_dir"])
    assert (pdir / "ElectricalModel.json").exists()


def test_conflict_triggers_approval(tmp_path):
    op = OrchestratedPipeline(workspace_root=tmp_path, backend="mock",
                              auto_approve=True)
    result = op.run(_requirement("p-conflict"))
    cr = result["conflict_report"]
    assert cr is not None
    if cr["requires_approval"]:
        approvals = json.loads(
            (Path(result["project_dir"]) / "approvals.json").read_text("utf-8"))
        assert approvals and approvals[0]["status"] == "APPROVED"


def test_runner_entry_point(tmp_path):
    runner = PipelineRunner(workspace_root=tmp_path, backend="mock")
    result = runner.run_orchestrated(_requirement("p-runner"))
    assert result["status"] == "COMPLETED"
    assert runner.task_graph is not None


def test_dynamic_no_manual_order(tmp_path):
    """仅给需求，不指定调用顺序，系统仍能自动排布依赖。"""
    req = ProjectRequirement(
        project_id="p-auto",
        target_schemas=["ValidationReport"],
        disciplines=["electrical", "plumbing"],
        inputs={"layout_model": _layout()},
    )
    op = OrchestratedPipeline(workspace_root=tmp_path, backend="mock")
    result = op.run(req)
    assert result["status"] == "COMPLETED"
    assert "electrical_task" in result["plan"]
    assert "plumbing_task" in result["plan"]
    assert "lighting_task" not in result["plan"]
