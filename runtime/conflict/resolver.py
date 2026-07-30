"""
runtime.conflict.resolver · Conflict Resolver（Phase 10 §5）。

处理专业间协调冲突（示例链：电路 → 水管 → 吊顶）：
    当多个专业在同一空间（room_id）内布置点位 / 管线 / 开洞时，
    存在需要人工确认的交叉协调问题。

输出：ConflictReport（含冲突清单），当存在冲突时 requires_approval=True，
需要进入 Human Approval 节点裁决。

禁止：AI 设计算法 / 施工规范知识库 / 真实碰撞检测算法（此处仅做规则式协调标记）。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


# 各专业参与“空间协调”的元素来源（字段 -> 元素类别）
_DISCIPLINE_ELEMENTS = {
    "ELECTRICAL": [("devices", "电气点位")],
    "PLUMBING": [("fixtures", "卫浴器具"), ("supply_pipes", "给水管"),
                 ("drain_pipes", "排水管")],
    "CEILING": [("openings", "吊顶开洞")],
    "LIGHTING": [("fixtures", "灯具")],
}

# 需要协调的专业对（无序）及说明
_CONFLICT_RULES = {
    frozenset({"ELECTRICAL", "PLUMBING"}):
        ("电气点位与给排水管线位于同一空间，需人工确认间距与交叉", "WARNING"),
    frozenset({"CEILING", "ELECTRICAL"}):
        ("吊顶开洞与电气点位可能交叉，需人工确认", "WARNING"),
    frozenset({"CEILING", "PLUMBING"}):
        ("吊顶开洞与给排水管线可能穿越冲突，需人工确认", "WARNING"),
    frozenset({"CEILING", "LIGHTING"}):
        ("吊顶开洞与灯具位置冲突（灯槽 / 检修口），需人工确认", "WARNING"),
    frozenset({"ELECTRICAL", "LIGHTING"}):
        ("电气回路与照明回路共处一室，需人工确认负荷与分回路", "INFO"),
}


@dataclass
class Conflict:
    conflict_id: str
    type: str
    disciplines: List[str]
    room_id: str
    description: str
    severity: str = "WARNING"
    items: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "type": self.type,
            "disciplines": list(self.disciplines),
            "room_id": self.room_id,
            "description": self.description,
            "severity": self.severity,
            "items": self.items,
        }


@dataclass
class ConflictReport:
    project_id: str
    status: str = "NO_CONFLICT"          # NO_CONFLICT / CONFLICTS_FOUND
    conflicts: List[Conflict] = field(default_factory=list)
    requires_approval: bool = False
    summary: Dict[str, Any] = field(default_factory=dict)
    report_id: str = field(default_factory=lambda: f"conf-{uuid.uuid4().hex[:8]}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "project_id": self.project_id,
            "status": self.status,
            "requires_approval": self.requires_approval,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "summary": self.summary,
        }


ModelsInput = Union[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]


class ConflictResolver:
    """规则式专业协调冲突检测器。"""

    def resolve(self, professional_models: ModelsInput,
                project_id: str = "") -> ConflictReport:
        models = self._normalize(professional_models)

        # discipline -> {room_id -> [元素引用]}
        by_room: Dict[str, Dict[str, List[str]]] = {}
        for disc, model in models.items():
            fields = _DISCIPLINE_ELEMENTS.get(disc)
            if not fields:
                continue
            room_map: Dict[str, List[str]] = {}
            for field_name, _label in fields:
                for el in model.get(field_name, []) or []:
                    rid = el.get("room_id")
                    if not rid:
                        continue
                    ref = (el.get("device_id") or el.get("fixture_id")
                           or el.get("opening_id") or el.get("pipe_id")
                           or el.get("light_id") or el.get("id") or field_name)
                    room_map.setdefault(rid, []).append(ref)
            if room_map:
                by_room[disc] = room_map

        conflicts: List[Conflict] = []
        disciplines = sorted(by_room.keys())
        for i in range(len(disciplines)):
            for j in range(i + 1, len(disciplines)):
                a, b = disciplines[i], disciplines[j]
                rule = _CONFLICT_RULES.get(frozenset({a, b}))
                if not rule:
                    continue
                desc, severity = rule
                shared_rooms = set(by_room[a]) & set(by_room[b])
                for rid in sorted(shared_rooms):
                    conflicts.append(Conflict(
                        conflict_id=f"CFL-{a[:3]}-{b[:3]}-{rid}",
                        type=f"{a}_x_{b}",
                        disciplines=[a, b],
                        room_id=rid,
                        description=f"{desc}（房间 {rid}）",
                        severity=severity,
                        items={a: by_room[a][rid], b: by_room[b][rid]},
                    ))

        # INFO 级不强制审批；WARNING / CRITICAL 需人工确认
        blocking = [c for c in conflicts if c.severity in ("WARNING", "CRITICAL")]
        report = ConflictReport(
            project_id=project_id,
            status="CONFLICTS_FOUND" if conflicts else "NO_CONFLICT",
            conflicts=conflicts,
            requires_approval=bool(blocking),
            summary={
                "conflict_count": len(conflicts),
                "blocking_count": len(blocking),
                "disciplines": disciplines,
                "by_severity": self._count_by_severity(conflicts),
            },
        )
        return report

    # ---- 内部 ----
    @staticmethod
    def _normalize(models: ModelsInput) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        if isinstance(models, dict):
            for key, model in models.items():
                if not isinstance(model, dict):
                    continue
                disc = (model.get("discipline") or key or "").upper()
                if disc:
                    out[disc] = model
        else:
            for model in models:
                if not isinstance(model, dict):
                    continue
                disc = (model.get("discipline") or "").upper()
                if disc:
                    out[disc] = model
        return out

    @staticmethod
    def _count_by_severity(conflicts: List[Conflict]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for c in conflicts:
            out[c.severity] = out.get(c.severity, 0) + 1
        return out


__all__ = ["Conflict", "ConflictReport", "ConflictResolver"]
