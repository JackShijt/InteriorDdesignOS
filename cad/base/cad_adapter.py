"""CADAdapter（Phase 6 §2）— CAD 后端抽象接口。

所有 CAD 后端（Mock / AutoCAD / 未来插件）必须实现本接口的全部方法。
DrawingAgent 只依赖本抽象，不知道具体后端（Phase 6 §6：DrawingAgent 不感知 CAD 实现）。

禁止：本层不得 import runtime / orchestrator / agents / professional。
允许：core / 标准库 / 三方库。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

# 所有后端必须实现的接口方法（用于适配器自检 / 测试）
CAD_ADAPTER_METHODS: List[str] = [
    "connect", "disconnect", "open_document", "save", "close",
    "create_layer",
    "draw_line", "draw_polyline", "draw_arc", "draw_circle",
    "insert_block", "create_text", "create_dimension",
    "export",
]


class CADAdapter(ABC):
    """CAD 后端抽象基类。

    子类（MockAdapter / AutoCADAdapter）实现全部抽象方法。
    提供上下文管理器（connect↔disconnect）以便 try/finally 安全释放。
    """

    backend_name: str = "abstract"

    # ---- 连接 / 文档生命周期 ----
    @abstractmethod
    def connect(self) -> None:
        """建立与 CAD 软件 / 服务之间的连接（Phase 6 仅约定，不连接真实软件）。"""

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接并释放资源。"""

    @abstractmethod
    def open_document(self, name: str) -> "Any":
        """打开（或新建）一个图纸文档，返回 CADDocument。"""

    @abstractmethod
    def save(self, name: Optional[str] = None) -> Any:
        """保存当前文档。"""

    @abstractmethod
    def close(self) -> None:
        """关闭当前文档。"""

    # ---- 图层 ----
    @abstractmethod
    def create_layer(self, name: str, color: int = 7,
                     line_type: str = "Continuous") -> Dict[str, Any]:
        """创建图层。"""

    # ---- 几何图元 ----
    @abstractmethod
    def draw_line(self, start: Any, end: Any,
                  layer: Optional[str] = None) -> Dict[str, Any]:
        """绘制直线。start/end 为 [x, y] 坐标。"""

    @abstractmethod
    def draw_polyline(self, points: Any, layer: Optional[str] = None,
                      width: Optional[float] = None,
                      closed: bool = False) -> Dict[str, Any]:
        """绘制多段线（墙体等可用 width 表示厚度）。"""

    @abstractmethod
    def draw_arc(self, center: Any, radius: float, start_angle: float,
                 end_angle: float, layer: Optional[str] = None) -> Dict[str, Any]:
        """绘制圆弧。角度单位：度。"""

    @abstractmethod
    def draw_circle(self, center: Any, radius: float,
                    layer: Optional[str] = None) -> Dict[str, Any]:
        """绘制圆。"""

    # ---- 块 / 文字 / 标注 ----
    @abstractmethod
    def insert_block(self, block_ref: str, position: Any, scale: float = 1.0,
                     rotation: float = 0.0,
                     layer: Optional[str] = None) -> Dict[str, Any]:
        """插入块（门窗/家具/图框等）。"""

    @abstractmethod
    def create_text(self, text: str, position: Any, height: float = 300,
                    layer: Optional[str] = None) -> Dict[str, Any]:
        """创建文字标注。"""

    @abstractmethod
    def create_dimension(self, start: Any, end: Any, value: Optional[float] = None,
                         unit: str = "mm",
                         layer: Optional[str] = None) -> Dict[str, Any]:
        """创建尺寸标注。"""

    # ---- 导出 ----
    @abstractmethod
    def export(self, path: Optional[Path] = None) -> Any:
        """导出结果（Mock 后端写 drawing_command_log.json；AutoCAD 端生成 DWG）。"""

    # ---- 上下文管理 ----
    def __enter__(self) -> "CADAdapter":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.close()
        finally:
            self.disconnect()


__all__ = ["CADAdapter", "CAD_ADAPTER_METHODS"]
