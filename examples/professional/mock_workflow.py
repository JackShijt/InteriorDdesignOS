"""
Phase 5 §10 · Mock Workflow 演示（CLI 脚本，允许输出到终端）。

流程：
  LayoutModel（示例）
    ↓ Parallel Fan-out
  Electrical / Lighting / HVAC / Furniture
    ↓ Parallel Fan-in
  Validator（聚合校验）
    ↓
  Export（清单 + 校验报告）

用法：
  python examples/professional/mock_workflow.py [project_id]

禁止：AutoCAD MCP / DWG / 外部 AI（全部 Mock Logic）。
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from runtime.config import load_runtime_config  # noqa: E402
from runtime.pipeline import Pipeline  # noqa: E402

DEMO_DISCIPLINES = ["electrical", "lighting", "hvac", "furniture"]


def main(argv: list) -> int:
    project_id = argv[1] if len(argv) > 1 else (
        "demo-professional-" + datetime.now().strftime("%Y%m%d%H%M%S"))
    layout = REPO_ROOT / "schemas" / "examples" / "LayoutModel.example.json"

    cfg = load_runtime_config()
    pipeline = Pipeline(project_id, config=cfg)
    summary = pipeline.run_professional(layout_path=str(layout),
                                        disciplines=DEMO_DISCIPLINES)

    print(f"[Mock Workflow] project={project_id}")
    print(f"  state={summary['status']} stage={summary['current_stage']}")
    for tid, status in sorted(summary["tasks"].items()):
        print(f"  task {tid}: {status}")
    prof = summary.get("professional", {})
    print(f"  validation_passed={prof.get('validation_passed')}")
    print(f"  report={prof.get('report')}")
    return 0 if summary["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
