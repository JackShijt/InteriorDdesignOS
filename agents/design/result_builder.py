"""Design Agent 结果构造器（Phase 4）。

与 Parser 的 result_builder 保持一致：输出统一 `Result`，
success=True 时通过 output_model 传递 DesignSpec。
"""
from typing import Any, Dict, List, Optional

from agents.orchestrator.agent import Result


def build_result(model: Dict[str, Any],
                 quality: Optional[Dict[str, Any]] = None,
                 messages: Optional[List[str]] = None,
                 errors: Optional[List[str]] = None,
                 next_tasks: Optional[List[str]] = None) -> Result:
    """构造统一 Result（Design Agent 成功路径）。

    Args:
        model: 校验通过后的 DesignSpec（作为 output_model）。
        quality: 质量评分 dict。
        messages: 过程消息。
        errors: 错误信息（成功时应为 None）。
        next_tasks: 下游任务（设计阶段后进入 Layout，但本阶段不自动触发）。
    """
    return Result(
        success=True,
        output_model=model,
        messages=messages or [],
        quality=quality,
        next_tasks=next_tasks if next_tasks is not None else [],
    )


__all__ = ["build_result"]
