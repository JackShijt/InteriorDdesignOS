"""cad/mock — 内存 CAD 后端（测试 / 回放）。"""
from __future__ import annotations

from .mock_adapter import MockAdapter
from .mock_document import MockDocument

__all__ = ["MockAdapter", "MockDocument"]
