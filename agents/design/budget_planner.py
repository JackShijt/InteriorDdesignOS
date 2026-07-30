"""Budget Planner（Phase 4 §6）。

根据预算线索与面积，给出预算等级与分配建议。

不输出具体品牌报价，只给出等级与类别占比。
"""
from typing import Any, Dict, List


def plan_budget(req: Dict[str, Any], area_m2: float = 0.0,
                total_estimate: float = None) -> Dict[str, Any]:
    """规划预算等级与分配。

    Args:
        req: parse_requirement 的输出。
        area_m2: 套内面积（来自约束），用于估算。
        total_estimate: 若用户明确给出总额则直接使用。
    Returns:
        { "level": str, "currency": "CNY",
          "total_estimate": float|null, "allocation": [ {category, ratio, note} ] }
    """
    hints = req.get("budget_hints", []) or []
    if hints:
        level = hints[0]  # 取首个命中的等级
    else:
        level = "MEDIUM"  # 缺省中等

    # 单价假设（元/m2，硬装+基础），仅用于粗略估算
    unit = {"LOW": 800, "MEDIUM": 1500, "HIGH": 3000, "PREMIUM": 6000}
    if total_estimate is None and area_m2:
        total_estimate = round(unit[level] * float(area_m2), -3)

    allocation = [
        {"category": "硬装基础", "ratio": 0.40, "note": "墙顶地与水电"},
        {"category": "定制柜体", "ratio": 0.20, "note": "收纳系统"},
        {"category": "软装家具", "ratio": 0.20},
        {"category": "电器设备", "ratio": 0.15},
        {"category": "备用机动", "ratio": 0.05, "note": "不可预见费"},
    ]
    return {
        "level": level,
        "currency": "CNY",
        "total_estimate": total_estimate,
        "allocation": allocation,
    }


__all__ = ["plan_budget"]
