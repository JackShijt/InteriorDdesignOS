"""
InteriorDesignOS · ArtifactManager（Phase 5.1 §5）

统一管理 Agent 输出物（模型 JSON）的生命周期：

    Agent -> ProfessionalModel -> ArtifactManager -> workspace/artifacts

职责：
- save()    原子写入（tmp + os.replace），自动归档旧版本
- load()    读取 JSON -> dict
- exists()  存在性检查
- archive() 手动归档当前版本
- delete()  删除（可选先归档）

规则：
- Agent 禁止直接 json.dump / open 写工作区文件（PROJECT_RULES §数据流）
- 版本归档目录：<project>/archive/<name>.<UTC时间戳>.json
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArtifactError(Exception):
    """Artifact 生命周期错误。"""


class ArtifactManager:
    """按项目管理 artifact（模型 JSON）的保存 / 读取 / 版本归档。

    project_root: 项目工作区根（workspace/projects/<project_id>）。
    所有 name 均为相对 project_root 的相对路径，例如
    "professional/electrical_model.json"。
    """

    ARCHIVE_DIR = "archive"

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _resolve(self, name: str) -> Path:
        path = (self.project_root / name).resolve()
        root = self.project_root.resolve()
        if root not in path.parents and path != root:
            raise ArtifactError(f"artifact 路径越出项目工作区: {name}")
        return path

    def _archive_path(self, name: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
        rel = Path(name)
        return (self.project_root / self.ARCHIVE_DIR
                / rel.parent / f"{rel.stem}.{stamp}{rel.suffix or '.json'}")

    # ------------------------------------------------------------------ #
    # 公共接口
    # ------------------------------------------------------------------ #
    def save(self, name: str, data: Dict[str, Any],
             archive_previous: bool = True) -> Path:
        """原子保存 dict 为 JSON artifact；默认先归档旧版本。"""
        if not isinstance(data, dict):
            raise ArtifactError(
                f"artifact 数据必须是 dict，得到 {type(data).__name__}")
        path = self._resolve(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if archive_previous and path.exists():
            self.archive(name)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return path

    def load(self, name: str) -> Dict[str, Any]:
        """读取 artifact JSON -> dict。"""
        path = self._resolve(name)
        if not path.exists():
            raise ArtifactError(f"artifact 不存在: {name}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def exists(self, name: str) -> bool:
        return self._resolve(name).exists()

    def archive(self, name: str) -> Optional[Path]:
        """把当前版本复制到 archive/ 下（带 UTC 时间戳）。"""
        path = self._resolve(name)
        if not path.exists():
            return None
        target = self._archive_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        return target

    def delete(self, name: str, archive_first: bool = True) -> bool:
        """删除 artifact；默认先归档。"""
        path = self._resolve(name)
        if not path.exists():
            return False
        if archive_first:
            self.archive(name)
        path.unlink()
        return True

    def versions(self, name: str) -> List[Path]:
        """列出某 artifact 的全部归档版本（按时间升序）。"""
        rel = Path(name)
        arch_dir = self.project_root / self.ARCHIVE_DIR / rel.parent
        if not arch_dir.exists():
            return []
        return sorted(arch_dir.glob(f"{rel.stem}.*{rel.suffix or '.json'}"))


__all__ = ["ArtifactManager", "ArtifactError"]
