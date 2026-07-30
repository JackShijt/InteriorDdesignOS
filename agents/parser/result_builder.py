"""
InteriorDesignOS · Parser · Result Builder（Phase 3 §10）

Parser 返回统一 Result，禁止返回裸 dict。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.orchestrator.agent import Result


def build_result(
    model: Dict[str, Any],
    quality: Dict[str, Any],
    messages: Optional[List[str]] = None,
    next_tasks: Optional[List[str]] = None,
) -> Result:
    """构造 Parser 的成功 Result。

    - output_model: OriginalModel
    - next_tasks: 默认 ["design"]（进入 Phase 4 设计阶段）
    """
    return Result(
        success=True,
        output_model=model,
        messages=messages or [],
        quality=quality,
        next_tasks=next_tasks or ["design"],
    )


__all__ = ["build_result"]
