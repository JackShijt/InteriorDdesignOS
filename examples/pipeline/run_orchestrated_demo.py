"""examples.pipeline.run_orchestrated_demo · 动态编排流水线示例（Phase 10 §9）。

运行：python examples/pipeline/run_orchestrated_demo.py

演示“输入一个项目需求 → 系统自动完成建项 / 分析 / 规划 / 找 Agent / 执行 / 校验”，
不再由人工指定“先调用谁、后调用谁”。

输出：workspace/projects/orchestrated-project/
  orchestration_plan.json / task_graph.json / LayoutModel.json /
  ElectricalModel.json / LightingModel.json / PlumbingModel.json /
  CeilingModel.json / GeometryModel.json / DrawingModel.json /
  ConflictReport.json / approvals.json / ValidationReport.json / GeneratedModel.json
"""
import json
import sys
from pathlib import Path

# 允许仓库根目录直接运行
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.pipeline import PipelineRunner  # noqa: E402
from runtime.orchestrator.task_planner import ProjectRequirement  # noqa: E402


def main() -> None:
    demo = ROOT / "examples" / "pipeline" / "professional_demo.json"
    layout = json.loads(demo.read_text(encoding="utf-8"))

    # 一个“项目需求”：只描述已有数据 / 目标产物 / 需覆盖专业，不指定调用顺序
    requirement = ProjectRequirement(
        project_id="orchestrated-project",
        name="100㎡三居室·动态编排",
        goal="full_drawing",
        initial_schemas=["DesignSpec"],
        target_schemas=["DrawingModel", "ValidationReport"],
        disciplines=["electrical", "lighting", "plumbing", "ceiling"],
        inputs={"layout_model": layout},
    )

    runner = PipelineRunner(workspace_root=ROOT / "workspace", backend="mock")
    result = runner.run_orchestrated(requirement)

    print("=== Phase 10 Orchestrated Pipeline Demo ===")
    print("status        :", result.get("status"))
    print("project_id    :", result.get("project_id"))
    print("project_dir   :", result.get("project_dir"))
    print("plan (auto)   :", " -> ".join(result.get("plan", [])))
    print("professional  :", ", ".join(result.get("professional_models", [])))
    print("validation    :", result.get("validation_status"))
    print("command_count :", result.get("command_count"))
    cr = result.get("conflict_report")
    if cr:
        print("conflicts     :", cr.get("summary", {}).get("conflict_count"),
              "| requires_approval:", cr.get("requires_approval"))
    print("tasks         :")
    for tid, st in (result.get("tasks") or {}).items():
        print(f"  - {tid:16s}: {st}")
    print("messages:")
    for m in (result.get("messages") or []):
        print("  *", m)
    if result.get("status") not in ("COMPLETED", "WAITING_USER"):
        print("ERROR:", result.get("error"))
        sys.exit(1)


if __name__ == "__main__":
    main()
