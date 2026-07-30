"""mcp.cad_adapter.dwg_bridge · DWG → GeneratedModel 桥接（Phase 13 §10）。

第一阶段（Phase 13）只建立接口，不实现完整 DWG 内核：
- ``DWGBridge`` 为抽象接口（``read`` / ``generate_model``）。
- ``ReferenceDWGBridge`` 为**参考实现**：读取由 SimulatedTransport 写出的
  DWG manifest 副本来重建 ``GeneratedModel``。它不解析真实 DWG 二进制，
  仅用于离线闭环验证（Test 3）。真实部署应替换为对接
  ``puran-water/autocad-mcp`` 的 ``READ_ENTITY`` / DWG 解析能力。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.cad_adapter.exceptions import DWGBridgeError

# AutoCAD MCP 工具动作 → GeneratedModel 实体类别
_TOOL_ACTION_TO_KIND = {
    "draw_line": "line",
    "draw_polyline": "polyline",
    "add_text": "text",
    "add_dimension": "dimension",
    "create_insert": "block",
    "create_layer": "layer",
}


class DWGBridge(ABC):
    """DWG → GeneratedModel 抽象接口（Phase 13 仅定义）。"""

    @abstractmethod
    def read(self, path: str) -> Dict[str, Any]:
        """读取 DWG 文件，返回原始实体集合（真实解析未实现）。"""

    @abstractmethod
    def generate_model(self, path: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """DWG → GeneratedModel（Phase 13 闭环末端）。"""


class ReferenceDWGBridge(DWGBridge):
    """参考实现：从 DWG manifest 副本身建 GeneratedModel。

    仅用于离线闭环验证；不解析真实 DWG 二进制。
    """

    def read(self, path: str) -> Dict[str, Any]:
        manifest = self._manifest_path(path)
        if not manifest.exists():
            raise DWGBridgeError(
                f"无法读取 DWG（真实 DWG 解析未实现）：{path}。"
                f"请接入 autocad-mcp 的 READ_ENTITY/DWG 解析能力。")
        return json.loads(manifest.read_text(encoding="utf-8"))

    def generate_model(self, path: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        manifest = self._manifest_path(path)
        if not manifest.exists():
            raise DWGBridgeError(
                f"DWG manifest 缺失（真实 DWG 解析未实现）：{manifest}。"
                f"请接入 autocad-mcp 的 READ_ENTITY / DWG 解析能力。")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        raw_entities = data.get("entities", [])

        entities: List[Dict[str, Any]] = []
        counts = {k: 0 for k in
                  ("line", "polyline", "text", "dimension", "block", "layer")}
        for e in raw_entities:
            action = (e.get("type") or "").split(".")[-1]
            kind = _TOOL_ACTION_TO_KIND.get(action, "other")
            if kind in counts:
                counts[kind] += 1
            entities.append({
                "entity_id": e.get("ref"),
                "handle": e.get("handle"),
                "kind": kind,
                "source_type": e.get("type"),
            })

        return {
            "dwg_path": str(path),
            "source": {"adapter": "mcp.cad_adapter", "backend": "autocad-mcp"},
            "project_id": project_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "layers": [],
            "entities": entities,
            "dimensions": [e for e in entities if e["kind"] == "dimension"],
            "counts": {**counts, "total": len(entities)},
        }

    @staticmethod
    def _manifest_path(path: str) -> Path:
        p = Path(path)
        return p.with_suffix(p.suffix + ".manifest.json")


__all__ = ["DWGBridge", "ReferenceDWGBridge"]
