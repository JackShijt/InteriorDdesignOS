"""
runtime.orchestrator · 动态编排层（Phase 10 §2）。

包含：
  - task_planner：由 ProjectRequirement 动态生成 TaskGraph（数据流驱动，禁止硬编码顺序）。
"""
from runtime.orchestrator.task_planner import ProjectRequirement, TaskPlanner

__all__ = ["ProjectRequirement", "TaskPlanner"]
