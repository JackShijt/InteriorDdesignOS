"""Material Planner（Phase 4 §8）。

仅输出材料偏好（地面 / 墙面 / 顶面等），禁止品牌推荐。
"""
from typing import Any, Dict, List

# 需求关键词 -> 材料规格
_KEYWORDS = {
    "木地板": ("地面", "木地板"),
    "地板": ("地面", "木地板"),
    "瓷砖": ("地面", "瓷砖"),
    "地砖": ("地面", "瓷砖"),
    "岩板": ("厨房墙面", "岩板"),
    "大理石": ("地面", "大理石"),
    "乳胶漆": ("墙面", "乳胶漆"),
    "艺术漆": ("墙面", "艺术漆"),
    "微水泥": ("墙面", "微水泥"),
    "护墙板": ("墙面", "护墙板"),
    "木饰面": ("墙面", "木饰面"),
}


def plan_materials(req: Dict[str, Any],
                   constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """规划材料偏好。

    Args:
        req: parse_requirement 的输出。
        constraints: parse_constraints 的输出（用于防潮等附加建议）。
    Returns:
        材料列表，每项 { category, spec, brand_recommended: false }
        严禁输出任何品牌名称。
    """
    text = req.get("raw_text", "") or ""
    constraints = constraints or {}
    materials: List[Dict[str, Any]] = []
    seen = set()

    for kw, (cat, spec) in _KEYWORDS.items():
        if kw in text:
            key = (cat, spec)
            if key not in seen:
                seen.add(key)
                materials.append({"category": cat, "spec": spec,
                                  "brand_recommended": False})

    # 缺省：给出一套稳妥的中性方案（仍不推荐品牌）
    if not materials:
        materials = [
            {"category": "地面", "spec": "木地板", "brand_recommended": False},
            {"category": "墙面", "spec": "乳胶漆", "brand_recommended": False},
        ]

    # 朝向 / 采光导致的附加建议（不引入品牌）
    orient = constraints.get("orientation")
    if orient in ("南", "东"):
        materials.append({"category": "顶面", "spec": "乳胶漆/极简吊顶",
                          "brand_recommended": False})
    return materials


__all__ = ["plan_materials"]
