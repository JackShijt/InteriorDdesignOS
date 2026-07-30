"""agents.construction · 施工深化 Agent（Phase 9 §2）。

输入：LayoutModel
输出：ConstructionModel（强类型 dict）

业务：依据房间类型派生墙体 / 地面 / 顶面饰面做法与施工项。
禁止：直接输出 DWG / 调用 AutoCAD。
"""
from typing import Any, Dict, List

from core.context import AgentContext, BaseAgent, Result
from models.professional.construction import ConstructionModel

# 地面做法：湿区用瓷砖，其他用木地板
WET_ROOM_TYPES = {"kitchen", "bathroom", "balcony", "wc", "toilet", "utility"}


class ConstructionAgent(BaseAgent):
    agent_name = "construction"
    version = "1.0"

    def run(self, context: AgentContext) -> Result:
        layout = context.inputs.get("layout_model") or {}
        try:
            content = self.transform(layout)
            model = ConstructionModel(
                discipline="CONSTRUCTION",
                items=content["items"],
                finishes=content["finishes"],
                summary=content["summary"],
            )
            model.stamp(context, producer_agent=self.agent_name)
            msg = (f"Construction: {len(content['items'])} 施工项 / "
                   f"{len(content['finishes'])} 饰面做法")
            return Result(success=True, output_model=model.to_dict(), messages=[msg])
        except Exception as e:  # noqa: BLE001
            return Result(success=False, messages=[f"ConstructionAgent 失败：{e}"])

    # ------------------------------------------------------------------ #
    @staticmethod
    def transform(layout: Dict[str, Any]) -> Dict[str, Any]:
        rooms = layout.get("rooms", [])
        items: List[Dict[str, Any]] = []
        finishes: List[Dict[str, Any]] = []
        for i, room in enumerate(rooms, 1):
            rid = room.get("room_id", f"R{i}")
            name = room.get("name", "")
            rtype = (room.get("type") or "").lower()
            floor_mat = "瓷砖" if rtype in WET_ROOM_TYPES else "实木复合地板"
            finishes.append({
                "finish_id": f"FN-FLOOR-{rid}",
                "category": "FLOOR",
                "room_id": rid,
                "room_name": name,
                "material": floor_mat,
                "spec": "满铺",
                "layer": "CONST-FLOOR",
            })
            finishes.append({
                "finish_id": f"FN-WALL-{rid}",
                "category": "WALL",
                "room_id": rid,
                "room_name": name,
                "material": "乳胶漆",
                "spec": "两底两面",
                "layer": "CONST-WALL",
            })
            items.append({
                "item_id": f"CI-{rid}",
                "category": "WALL",
                "room_id": rid,
                "room_name": name,
                "spec": "新建轻质隔墙",
                "quantity": 1,
                "layer": "CONST-ITEM",
            })
        return {
            "items": items,
            "finishes": finishes,
            "summary": {"item_count": len(items),
                        "finish_count": len(finishes)},
        }
