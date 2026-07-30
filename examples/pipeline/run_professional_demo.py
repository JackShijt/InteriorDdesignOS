"""examples.pipeline.run_professional_demo · 专业深化流水线示例（Phase 9 §7）。

运行：python examples/pipeline/run_professional_demo.py
输出：workspace/projects/project/
  LayoutModel.json / ElectricalModel.json / LightingModel.json /
  PlumbingModel.json / GeometryModel.json / DrawingModel.json /
  ValidationReport.json（+ Ceiling/Construction/Elevation/Generated 等）
"""
import json
import sys
from pathlib import Path

# 允许仓库根目录直接运行
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.pipeline import PipelineRunner  # noqa: E402


def main() -> None:
    demo = ROOT / "examples" / "pipeline" / "professional_demo.json"
    layout = json.loads(demo.read_text(encoding="utf-8"))

    runner = PipelineRunner(workspace_root=ROOT / "workspace", backend="mock")
    result = runner.run_professional(
        layout, project_id="project", name="100㎡三居室·专业深化")

    print("=== Phase 9 Professional Pipeline Demo ===")
    print("status        :", result.get("status"))
    print("project_id    :", result.get("project_id"))
    print("project_dir   :", result.get("project_dir"))
    print("validation    :", result.get("validation_status"))
    print("command_count :", result.get("command_count"))
    print("professional  :")
    for k, v in (result.get("professional_models") or {}).items():
        print(f"  - {k:12s}: {v}")
    print("messages:")
    for m in (result.get("messages") or []):
        print("  *", m)
    if result.get("status") != "COMPLETED":
        print("ERROR:", result.get("error"))
        sys.exit(1)


if __name__ == "__main__":
    main()
