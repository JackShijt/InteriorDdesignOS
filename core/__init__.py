"""
InteriorDesignOS · Core Package（Phase 5.1）

架构基础层：不依赖 runtime / orchestrator / professional 的最底层共享包。

依赖规则（docs/PROFESSIONAL_FRAMEWORK.md · Dependency Rules）：

    Runtime -> Orchestrator -> Agent -> RuleEngine -> Model
                     \\_________________ core _________________/

core 只能被上层依赖，禁止 core 反向 import 任何上层包。
"""
from pathlib import Path

# 仓库根目录 = core/ 的父目录
REPO_ROOT = Path(__file__).resolve().parent.parent

# 默认工作区目录（与 runtime 保持一致的物理位置，但独立计算，避免依赖 runtime）
WORKSPACE_ROOT = REPO_ROOT / "workspace"
PROJECTS_DIR = WORKSPACE_ROOT / "projects"

__all__ = ["REPO_ROOT", "WORKSPACE_ROOT", "PROJECTS_DIR"]
