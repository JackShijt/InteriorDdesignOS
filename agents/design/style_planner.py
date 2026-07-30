"""Style Planner（Phase 4 §5）。

将需求中的风格线索映射为风格标签（允许多个）。

禁止直接生成布局 / 几何 / CAD（§5、§17）：仅输出语义标签与描述。
"""
from typing import Any, Dict, List

_ALLOWED = {"Modern", "Minimal", "Nordic", "Japanese", "Industrial",
            "Chinese", "Luxury", "Mixed"}


def plan_style(req: Dict[str, Any]) -> Dict[str, Any]:
    """根据 UserRequirement 规划风格。

    Args:
        req: parse_requirement 的输出（dict）。
    Returns:
        { "labels": [str], "description": str }
        labels 必含至少 1 个枚举值（缺省为 ["Mixed"]）。
    """
    hints = req.get("style_hints", []) or []
    labels = [h for h in hints if h in _ALLOWED]
    if not labels:
        labels = ["Mixed"]

    desc_parts = []
    if "Nordic" in labels:
        desc_parts.append("浅木色 + 中性灰，强调自然采光与极简收纳")
    if "Modern" in labels:
        desc_parts.append("干净线条与开放空间")
    if "Minimal" in labels:
        desc_parts.append("少即是多，弱化装饰")
    if "Japanese" in labels:
        desc_parts.append("温润材质与留白")
    if "Industrial" in labels:
        desc_parts.append("裸露材质与冷调肌理")
    if "Chinese" in labels:
        desc_parts.append("东方意境与对称秩序")
    if "Luxury" in labels:
        desc_parts.append("高级材质与精细收口")
    if "Mixed" in labels and len(labels) == 1:
        desc_parts.append("风格未定 / 混搭，待与用户进一步确认")
    description = "；".join(desc_parts) if desc_parts else "用户未指定明确风格"

    return {"labels": labels, "description": description}


__all__ = ["plan_style"]
