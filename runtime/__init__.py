"""
InteriorDesignOS · Runtime Package

本模块遵守 PROJECT_RULES.md 的最高约束。

运行时支撑层（PROCESS_RULES §4、§10、§11）：
- 工程运行状态的持久化（ProjectRuntime）
- 统一日志（logger）
- 发布/订阅事件总线（event_bus / message）
- 会话聚合（session）

本包为「存储 / 运行时」支撑，不反向依赖 agents/orchestrator（PROJECT_RULES §2.1 分层解耦）。
"""

from pathlib import Path

# 仓库根目录 = runtime/ 的父目录
REPO_ROOT = Path(__file__).resolve().parent.parent

# 工作区目录（PROJECT_RULES §11、ARCHITECTURE §3）
WORKSPACE_ROOT = REPO_ROOT / "workspace"
PROJECTS_DIR = WORKSPACE_ROOT / "projects"
CACHE_DIR = WORKSPACE_ROOT / "cache"
LOG_DIR = WORKSPACE_ROOT / "logs"
ARTIFACTS_DIR = WORKSPACE_ROOT / "artifacts"


def ensure_workspace() -> None:
    """第一次运行自动创建 workspace 子目录（Phase 2 §3）。"""
    for d in (PROJECTS_DIR, CACHE_DIR, LOG_DIR, ARTIFACTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


__all__ = [
    "REPO_ROOT",
    "WORKSPACE_ROOT",
    "PROJECTS_DIR",
    "CACHE_DIR",
    "LOG_DIR",
    "ARTIFACTS_DIR",
    "ensure_workspace",
]
