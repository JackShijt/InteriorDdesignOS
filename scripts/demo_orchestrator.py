#!/usr/bin/env python3
"""
Phase 2 演示脚本：Orchestrator Framework 端到端跑通

本脚本为「驱动程序」（非框架内部），允许向终端打印运行结果以验证完成标准。

演示内容（对应 Phase 2 §15 完成标准）：
  ✓ 创建 Project
  ✓ 创建 TaskGraph（12 阶段 DAG）
  ✓ 调度虚拟 Agent
  ✓ 切换 Stage
  ✓ 保存 Checkpoint
  ✓ 恢复 Project（再次运行同 project_id）
  ✓ 输出日志（workspace/logs/）
  ✓ 发布事件（TaskCreated/Started/Finished/StageChanged/ProjectFinished）
  ✓ 管理 Context（layout/geometry/drawing/validation 快照）
  ✓ 整个框架完整运行

运行：
  cd InteriorDesignOS && python3 scripts/demo_orchestrator.py
"""

import sys
from pathlib import Path

# 仓库根目录加入路径
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.orchestrator import (  # noqa: E402
    Orchestrator, AgentRegistry, StubAgent, BaseAgent, Result, AgentContext,
)
from runtime.message import EventType  # noqa: E402


def banner(title: str) -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


def demo_full_run() -> None:
    banner("1) 新建 Project + 完整运行（虚拟 Agent）")
    orch = Orchestrator(project_id="demo", name="示例工程")
    summary = orch.run()
    print(f"status        : {summary['status']}")
    print(f"current_stage : {summary['current_stage']}")
    print(f"task 数       : {len(summary['tasks'])}")
    print(f"事件数        : {summary['events']}")
    print(f"检查点文件    : {summary['checkpoints']}")
    # 统计事件类型
    counts = {}
    for ev in orch.events:
        counts[ev["type"]] = counts.get(ev["type"], 0) + 1
    print(f"事件分布      : {counts}")


def demo_recovery() -> None:
    banner("2) 恢复 Project（再次运行同 project_id，已完成阶段被跳过）")
    orch = Orchestrator(project_id="demo")
    summary = orch.run()
    print(f"status        : {summary['status']}")
    print(f"current_stage : {summary['current_stage']}")
    print(f"检查点文件    : {summary['checkpoints']}")


def demo_failure_handling() -> None:
    banner("3) 异常归一（虚拟 Agent 返回失败 → 框架不崩溃、归入 FAILED）")

    class FailingAgent(StubAgent):
        def run(self, context: AgentContext) -> Result:
            return Result(success=False, messages=["模拟业务失败"])

    reg = AgentRegistry()
    # 仅让 VALIDATION 阶段失败，其余用 stub
    for s in ["INITIALIZATION", "INPUT_ANALYSIS", "ORIGINAL_MODEL", "DESIGN_SPEC",
              "LAYOUT", "PROFESSIONAL_DEEPENING", "GEOMETRY", "DRAWING",
              "DWG_GENERATION", "VALIDATION", "REPAIR", "EXPORT"]:
        if s == "VALIDATION":
            reg.register(FailingAgent(agent_name="validation"))
        else:
            reg.register(StubAgent(agent_name=s.lower()))

    orch = Orchestrator(project_id="demo_fail", registry=reg)
    summary = orch.run()
    print(f"status        : {summary['status']}  (期望 FAILED)")
    failed = [tid for tid, st in summary["tasks"].items() if st == "FAILED"]
    print(f"FAILED 任务   : {failed}")


def main() -> None:
    demo_full_run()
    demo_recovery()
    demo_failure_handling()
    banner("Phase 2 完成标准已逐项验证（详见上方输出与 workspace/logs/）")
    # 列出日志文件，证明「可以输出日志」
    log_dir = REPO_ROOT / "workspace" / "logs"
    if log_dir.exists():
        print(f"日志文件: {sorted(p.name for p in log_dir.glob('*.log'))}")


if __name__ == "__main__":
    main()
