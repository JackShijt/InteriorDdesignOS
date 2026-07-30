"""MockAdapter（Phase 6 §5）— 内存 CAD 后端。

功能：
- 实现 CADAdapter 全部接口（记录执行历史，不连接真实软件）
- export() 输出 drawing_command_log.json（用于测试 / 回放）

绘制方法只把调用记录进 execution_log 并返回记录 dict，
真正「画图」由未来后端（AutoCAD MCP）负责。这正是 Phase 6 的边界：
抽象层到位、后端可插拔、Mock 可运行。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base.cad_adapter import CADAdapter
from .mock_document import MockDocument


class MockAdapter(CADAdapter):
    backend_name = "mock"

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else None
        self.connected = False
        self.document: Optional[MockDocument] = None
        self.execution_log: List[Dict[str, Any]] = []

    # ---- 连接 / 文档 ----
    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def open_document(self, name: str) -> MockDocument:
        self.document = MockDocument(name, self)
        return self.document

    def save(self, name: Optional[str] = None) -> Any:
        return self.export()

    def close(self) -> None:
        if self.document:
            self.document.is_open = False

    # ---- 图层 ----
    def create_layer(self, name: str, color: int = 7,
                     line_type: str = "Continuous") -> Dict[str, Any]:
        rec = {"op": "create_layer", "layer": name,
               "color": color, "line_type": line_type}
        self._record(rec)
        if self.document:
            self.document.add_layer(name, color, line_type)
        return rec

    # ---- 几何图元 ----
    def draw_line(self, start: Any, end: Any,
                  layer: Optional[str] = None) -> Dict[str, Any]:
        rec = {"op": "draw_line", "start": start, "end": end, "layer": layer}
        return self._record(rec)

    def draw_polyline(self, points: Any, layer: Optional[str] = None,
                      width: Optional[float] = None,
                      closed: bool = False) -> Dict[str, Any]:
        rec = {"op": "draw_polyline", "points": points, "layer": layer,
               "width": width, "closed": closed}
        return self._record(rec)

    def draw_arc(self, center: Any, radius: float, start_angle: float,
                 end_angle: float,
                 layer: Optional[str] = None) -> Dict[str, Any]:
        rec = {"op": "draw_arc", "center": center, "radius": radius,
               "start_angle": start_angle, "end_angle": end_angle,
               "layer": layer}
        return self._record(rec)

    def draw_circle(self, center: Any, radius: float,
                    layer: Optional[str] = None) -> Dict[str, Any]:
        rec = {"op": "draw_circle", "center": center, "radius": radius,
               "layer": layer}
        return self._record(rec)

    # ---- 块 / 文字 / 标注 ----
    def insert_block(self, block_ref: str, position: Any, scale: float = 1.0,
                     rotation: float = 0.0,
                     layer: Optional[str] = None) -> Dict[str, Any]:
        rec = {"op": "insert_block", "block_ref": block_ref,
               "position": position, "scale": scale, "rotation": rotation,
               "layer": layer}
        return self._record(rec)

    def create_text(self, text: str, position: Any, height: float = 300,
                    layer: Optional[str] = None) -> Dict[str, Any]:
        rec = {"op": "create_text", "text": text, "position": position,
               "height": height, "layer": layer}
        return self._record(rec)

    def create_dimension(self, start: Any, end: Any,
                         value: Optional[float] = None, unit: str = "mm",
                         layer: Optional[str] = None) -> Dict[str, Any]:
        rec = {"op": "create_dimension", "start": start, "end": end,
               "value": value, "unit": unit, "layer": layer}
        return self._record(rec)

    # ---- 导出 ----
    def export(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """导出执行历史；若给定 path 或 output_dir，则写入 drawing_command_log.json。"""
        log: Dict[str, Any] = {
            "backend": self.backend_name,
            "command_count": len(self.execution_log),
            "log": self.execution_log,
        }
        target = Path(path) if path else (
            self.output_dir / "drawing_command_log.json" if self.output_dir
            else None)
        if target:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(log, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8")
        return log

    # ---- 内部 ----
    def _record(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        self.execution_log.append(rec)
        return rec


__all__ = ["MockAdapter"]
