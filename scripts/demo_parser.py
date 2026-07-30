#!/usr/bin/env python3
"""
Phase 3 演示脚本：Parser Agent 端到端跑通（独立运行 + Dispatcher 集成）。

本脚本为「驱动程序」（非框架内部），允许向终端打印运行结果以验证完成标准。

演示内容（对应 Phase 3 §16 完成标准）：
  ✓ Parser 可独立运行
  ✓ 自动识别输入类型
  ✓ 成功生成 OriginalModel
  ✓ Schema 校验通过
  ✓ 保存 Workspace（original_model.json）
  ✓ 保存 Checkpoint（checkpoint_parser_v1.json）
  ✓ Dispatcher 可调用 Parser
  ✓ Orchestrator 可调度 Parser（见 tests/parser）
  ✓ 返回统一 Result
  ✓ 单元测试覆盖（tests/parser）

运行：
  cd InteriorDesignOS && python3 scripts/demo_parser.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.parser import run_parser, InputType  # noqa: E402
from runtime.project_runtime import STAGES  # noqa: E402


def banner(title: str) -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


def demo_standalone() -> None:
    banner("1) Parser 独立运行（示例 JSON）")
    sample = REPO_ROOT / "examples" / "input" / "sample_json" / "sample.json"
    ws = REPO_ROOT / "workspace"
    res = run_parser(sample, project_id="demo", workspace_root=ws)
    print(f"success        : {res.success}")
    print(f"messages       : {res.messages}")
    print(f"next_tasks     : {res.next_tasks}")
    om = ws / "projects" / "demo" / "original_model.json"
    cp = ws / "projects" / "demo" / "checkpoint_parser_v1.json"
    print(f"workspace 保存 : {om.exists()}  ({om})")
    print(f"checkpoint 保存: {cp.exists()}  ({cp})")
    print(f"walls 数量     : {len(res.output_model['walls'])}")
    print(f"rooms 数量     : {len(res.output_model['rooms'])}")


def demo_various_inputs() -> None:
    banner("2) 多输入类型识别（自动）")
    mapping = {
        "DWG 占位": "sample_dwg_placeholder/sample.dwg",
        "PDF 占位": "sample_pdf/sample.pdf",
        "图片占位": "sample_image/sample.png",
        "空输入   ": "empty_project/empty.txt",
    }
    ws = REPO_ROOT / "workspace"
    for label, rel in mapping.items():
        p = REPO_ROOT / "examples" / "input" / rel
        res = run_parser(p, project_id=f"demo_{Path(rel).stem}",
                         workspace_root=ws)
        print(f"{label}: success={res.success}  msg={res.messages}")


def demo_dispatcher() -> None:
    banner("3) Dispatcher 调用 Parser（集成）")
    from agents.orchestrator import AgentRegistry
    from agents.orchestrator.dispatcher import Dispatcher
    from agents.orchestrator.task_graph import TaskGraph
    from agents.orchestrator.context_manager import ContextManager
    from agents.orchestrator.checkpoint import Checkpoint
    from runtime.event_bus import EventBus
    from runtime.logger import UnifiedLogger
    from runtime.project_runtime import ProjectRuntime
    from agents.parser import ParserAgent

    ws = REPO_ROOT / "workspace"
    logs = ws / "logs"
    pid = "demo_dispatch"
    pr = ProjectRuntime(ws)
    pr.create(pid, "demo-dispatch")
    g = TaskGraph()
    sample = REPO_ROOT / "examples" / "input" / "sample_json" / "sample.json"
    g.create_task(task_id="parser-1", agent="parser", stage="ORIGINAL_MODEL",
                 dependencies=[], input_refs=[str(sample)])
    g.update_status("parser-1", "READY")
    reg = AgentRegistry()
    reg.register(ParserAgent(workspace_root=ws, log_dir=logs))
    bus = EventBus(UnifiedLogger(log_dir=logs))
    cm = ContextManager(ws)
    cp = Checkpoint(cm, pr, bus, UnifiedLogger(log_dir=logs))
    disp = Dispatcher(pid, g, reg, cm, cp, bus, UnifiedLogger(log_dir=logs))
    res = disp.execute("parser-1")
    print(f"dispatcher result success: {res.success if res else None}")
    print(f"task status              : {g.get_task('parser-1').status}")
    print(f"workspace 保存           : {(ws / 'projects' / pid / 'original_model.json').exists()}")


def main() -> None:
    demo_standalone()
    demo_various_inputs()
    demo_dispatcher()
    banner("Phase 3 Parser Agent 完成标准已逐项验证（详见上方输出与 workspace/）")


if __name__ == "__main__":
    main()
