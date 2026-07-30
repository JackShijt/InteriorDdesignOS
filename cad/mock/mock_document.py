"""MockDocument（Phase 6 §5）— Mock 后端的内存文档。

仅用于测试 / 内存态记录；不落盘（落盘由 MockAdapter.export 负责）。
"""
from __future__ import annotations

from typing import Any, Dict

from ..base.cad_document import CADDocument


class MockDocument(CADDocument):
    """Mock 后端文档：在 CADDocument 基础上提供 dump 便于断言。"""

    def dump(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "layers": self.layers,
            "entities": self.entities,
        }


__all__ = ["MockDocument"]
