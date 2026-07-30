"""Family Analyzer（Phase 4 §7）。

从 UserRequirement 推导家庭画像 `FamilyProfile`。
"""
from typing import Any, Dict, List


def analyze_family(req: Dict[str, Any]) -> Dict[str, Any]:
    """推导家庭画像。

    Args:
        req: parse_requirement 的输出。
    Returns:
        { adults, children, elders, pets, work_from_home, accessibility, notes }
    """
    fam = req.get("family_hints", {}) or {}
    adults = int(fam.get("adults_hint", 2))
    children = 1 if fam.get("children") else 0
    elders = 1 if fam.get("elders") else 0

    pets: List[str] = list(fam.get("pets_keywords", []))
    if fam.get("pets") and not pets:
        pets = ["宠物"]

    work_from_home = bool(fam.get("work_from_home"))
    accessibility = bool(fam.get("accessibility"))

    notes = []
    if children:
        notes.append("有儿童，需注意安全与圆角处理")
    if elders:
        notes.append("有老人，关注无障碍与适老化")
    if accessibility:
        notes.append("明确无障碍需求")
    if work_from_home:
        notes.append("居家办公，需独立工作区")

    return {
        "adults": adults,
        "children": children,
        "elders": elders,
        "pets": pets,
        "work_from_home": work_from_home,
        "accessibility": accessibility,
        "notes": "；".join(notes),
    }


__all__ = ["analyze_family"]
