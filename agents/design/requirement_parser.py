"""Requirement Parser（Phase 4 §3）。

将用户自然语言需求解析为结构化 `UserRequirement`。

只做抽取与归一化，不做任何布局 / 几何 / CAD 决策。
所有判断基于关键词规则（确定性，可测试），不调用 LLM。
"""
from typing import Any, Dict, List


# 关键词 -> 结构化字段 的确定性规则
_STYLE_MAP = {
    "现代": "Modern", "极简": "Minimal", "简约": "Minimal",
    "北欧": "Nordic", "日式": "Japanese", "日系": "Japanese",
    "工业风": "Industrial", "工业": "Industrial",
    "中式": "Chinese", "新中式": "Chinese",
    "轻奢": "Luxury", "奢华": "Luxury", "豪华": "Luxury",
    "混搭": "Mixed", "混风": "Mixed",
}
_BUDGET_MAP = {
    "低预算": "LOW", "经济": "LOW", "省钱": "LOW", "预算有限": "LOW", "预算低": "LOW",
    "中等预算": "MEDIUM", "预算中等": "MEDIUM", "适中": "MEDIUM",
    "普通预算": "MEDIUM", "中等": "MEDIUM",
    "高预算": "HIGH", "品质": "HIGH", "高端": "HIGH", "充足": "HIGH",
    "预算充足": "HIGH", "预算高": "HIGH",
    "豪装": "PREMIUM", "顶级": "PREMIUM", "不差钱": "PREMIUM", "预算充足顶级": "PREMIUM",
}
_FAMILY_KEYS = {
    "老人": "elders", "父母": "elders", "长辈": "elders",
    "小孩": "children", "孩子": "children", "儿童": "children",
    "宝宝": "children", "婴儿": "children",
    "宠物": "pets", "猫": "pets", "狗": "pets",
    "办公": "work_from_home", "居家办公": "work_from_home",
    "远程": "work_from_home", "无障碍": "accessibility",
    "轮椅": "accessibility", "适老": "accessibility",
}
_SPECIAL_KEYS = {
    "健身": "健身", "运动": "健身", "锻炼": "健身",
    "办公": "居家办公", "书房": "居家办公", "工作室": "居家办公",
    "宠物": "宠物友好", "猫": "养猫", "狗": "养狗",
    "老人": "老人照护", "长辈": "老人照护", "适老": "老人照护",
    "影音": "影音娱乐", "收藏": "收藏展示", "茶室": "茶室",
}
_LIGHTING_KEYS = {
    "采光": "natural", "自然光": "natural", "明亮": "bright",
    "温馨": "warm", "暖": "warm", "柔和": "soft", "中性": "neutral",
}
_COLOR_TOKENS = ["原木色", "白色", "浅灰", "米色", "灰色", "黑色",
                 "莫兰迪", "奶咖", "胡桃木", "橡木色", "雾蓝", "奶油"]


def _find(text: str, tokens: Dict[str, str]) -> List[str]:
    found = []
    for kw, val in tokens.items():
        if kw in text:
            found.append(val)
    return found


def parse_requirement(text: str) -> Dict[str, Any]:
    """解析用户自然语言需求 -> UserRequirement（dict）。

    Args:
        text: 用户需求原文（可为空字符串，返回缺省结构）。
    Returns:
        {
          "raw_text": str,
          "family_hints": {...},          # elders/children/pets/work_from_home/accessibility 计数/布尔
          "style_hints": [str],           # 风格标签枚举
          "budget_hints": [str],          # LOW/MEDIUM/HIGH/PREMIUM
          "room_preferences": [str],      # 提及的房间/功能
          "lighting_hints": [str],        # natural/warm/bright/soft/neutral
          "color_hints": [str],
          "storage_hints": [str],
          "special": [str],               # 健身/办公/宠物 等特殊需求
          "notes": str,
        }
    """
    text = (text or "").strip()
    req: Dict[str, Any] = {
        "raw_text": text,
        "family_hints": {},
        "style_hints": [],
        "budget_hints": [],
        "room_preferences": [],
        "lighting_hints": [],
        "color_hints": [],
        "storage_hints": [],
        "special": [],
        "notes": "",
    }
    if not text:
        req["notes"] = "未提供用户需求，使用缺省设计假设"
        return req

    req["style_hints"] = sorted(set(_find(text, _STYLE_MAP)))
    req["budget_hints"] = sorted(set(_find(text, _BUDGET_MAP)))

    # 家庭画像计数（老人/儿童/宠物按"几口/位/只"近似，这里只判存在）
    fam = {}
    # 人数：出现"X口之家"/"X人"时给出 adults 近似
    import re
    m = re.search(r"([1-9])人", text)
    if m:
        fam["adults_hint"] = int(m.group(1))
    for kw, key in _FAMILY_KEYS.items():
        if kw in text:
            fam[key] = True
    # 宠物具体种类
    for pet in ["猫", "狗"]:
        if pet in text and pet not in fam.get("pets_keywords", []):
            fam.setdefault("pets_keywords", []).append(pet)
    req["family_hints"] = fam

    # 房间/功能偏好
    room_kw = ["客厅", "餐厅", "厨房", "主卧", "次卧", "儿童房", "书房",
               "卫生间", "卫浴", "阳台", "衣帽间", "储物间", "影音室"]
    req["room_preferences"] = [r for r in room_kw if r in text]

    req["lighting_hints"] = sorted(set(_find(text, _LIGHTING_KEYS)))
    req["color_hints"] = [c for c in _COLOR_TOKENS if c in text]

    if "收纳" in text or "储藏" in text:
        req["storage_hints"].append("强收纳")
    if "断舍离" in text:
        req["storage_hints"].append("极简收纳")

    req["special"] = sorted(set(_find(text, _SPECIAL_KEYS)))
    # 去除与 family 重复的办公/宠物/老人标签（保留特殊需求语义）
    req["special"] = [s for s in req["special"]
                      if s not in ("居家办公", "宠物友好", "老人照护")
                      or s in text]
    return req


__all__ = ["parse_requirement"]
