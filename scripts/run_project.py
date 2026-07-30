#!/usr/bin/env python3
"""
scripts/run_project.py · 一个命令启动一个完整设计项目（Phase 11 §6）。

用法：
    python scripts/run_project.py examples/e2e/demo001.json
    python scripts/run_project.py examples/e2e/demo001.json --resume
    python scripts/run_project.py examples/e2e/demo001.json --workspace-root <dir>

输出（示例）：
    Project Started
    Stage: INITIALIZATION
    Running: parser
    Completed: OriginalModel
    Running: layout
    ...
    Project Delivered

说明：本脚本仅做 CLI 编排与日志打印，不实现任何业务逻辑 / 设计算法；
全部执行由 runtime.pipeline 的 E2EPipeline 驱动。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 仓库根加入 sys.path（确保以脚本任意位置调用均可导入）
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from runtime.event_bus import EventBus  # noqa: E402
from runtime.logger import UnifiedLogger  # noqa: E402
from runtime.message import Event, EventType  # noqa: E402
from runtime.pipeline import PipelineRunner  # noqa: E402


def _printer(event: Event) -> None:
    """将关键事件翻译为用户可见的阶段输出。"""
    t = event.type
    p = event.payload or {}
    if t == EventType.PROJECT_STARTED:
        print("Project Started")
        print("Stage:")
        print("  INITIALIZATION")
    elif t == EventType.STAGE_STARTED:
        print(f"Running:")
        print(f"  {p.get('agent')}")
    elif t == EventType.STAGE_COMPLETED:
        print(f"Completed:")
        print(f"  {p.get('output')}")
    elif t == EventType.PROJECT_COMPLETED:
        print("Project Delivered")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="运行一个完整 InteriorDesignOS 设计项目")
    parser.add_argument("requirement", help="项目需求 JSON 路径")
    parser.add_argument("--resume", action="store_true",
                        help="从中断处的检查点恢复执行")
    parser.add_argument("--workspace-root", default=None,
                        help="Workspace 根目录（默认 <repo>/examples/e2e/workspace）")
    args = parser.parse_args(argv)

    req_path = Path(args.requirement)
    if not req_path.exists():
        print(f"[ERROR] 需求文件不存在: {req_path}", file=sys.stderr)
        return 2
    requirement = json.loads(req_path.read_text(encoding="utf-8"))

    workspace_root = args.workspace_root or str(REPO_ROOT / "examples" / "e2e" / "workspace")
    (Path(workspace_root) / "logs").mkdir(parents=True, exist_ok=True)

    event_bus = EventBus(UnifiedLogger(log_dir=Path(workspace_root) / "logs"))
    event_bus.subscribe(EventType.PROJECT_STARTED, _printer)
    event_bus.subscribe(EventType.STAGE_STARTED, _printer)
    event_bus.subscribe(EventType.STAGE_COMPLETED, _printer)
    event_bus.subscribe(EventType.PROJECT_COMPLETED, _printer)

    runner = PipelineRunner(workspace_root=workspace_root)
    result = runner.run_e2e(requirement, resume=args.resume, event_bus=event_bus)

    print()
    print("==== 执行摘要 ====")
    print(f"Project ID : {result.get('project_id')}")
    print(f"Status     : {result.get('status')}")
    print(f"Artifacts  : {', '.join(result.get('artifacts', []))}")
    print(f"Professions: {', '.join(result.get('professional_models', []))}")
    print(f"CAD 命令   : {result.get('cad_command_count')}")
    conflict = result.get("conflict") or {}
    print(f"冲突数     : {conflict.get('summary', {}).get('conflict_count', 0)}")
    print(f"结果目录   : {result.get('project_dir')}")

    # ---- Phase 12：CAD Backend / DWG / Round-Trip 最终日志 ----
    print()
    backend = result.get("cad_backend") or "mock"
    print(f"CAD Backend: {'AutoCAD' if backend == 'autocad' else backend.capitalize()}")
    dwg = result.get("dwg") or {}
    if dwg.get("dwg_path"):
        print(f"DWG Generated: {dwg.get('dwg_path')}"
              + ("  (degraded)" if dwg.get("degraded") else ""))
    round_trip = result.get("round_trip") or {}
    if round_trip:
        rt = "PASSED" if round_trip.get("passed") else "FAILED"
        print(f"Round Trip Validation: {rt} "
              f"(coord_err={round_trip.get('max_coordinate_error_mm')}mm, "
              f"dim_err={round_trip.get('max_dimension_error_mm')}mm)")
    if result.get("status") == "DELIVERED":
        print("Project Delivered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
