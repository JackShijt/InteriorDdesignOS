"""examples.pipeline.run_demo · 端到端流水线示例（Phase 8 §5）。

运行：
    python3 examples/pipeline/run_demo.py

输出目录：workspace/projects/demo/
    - project.json
    - LayoutModel.json
    - GeometryModel.json
    - DrawingModel.json
    - drawing_command_log.json
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from runtime.pipeline import PipelineRunner  # noqa: E402


def main() -> int:
    demo = REPO / "examples" / "pipeline" / "demo_project.json"
    layout = json.loads(demo.read_text(encoding="utf-8"))

    runner = PipelineRunner(workspace_root=REPO / "workspace", backend="mock")
    summary = runner.run(layout, project_id="demo", name="100\u33a1\u4e09\u5c45\u5ba4")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
