"""Phase 10 §8 · 冲突处理测试。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.conflict import ConflictResolver, ConflictReport  # noqa: E402


def _models_with_conflict():
    return {
        "ELECTRICAL": {
            "discipline": "ELECTRICAL",
            "devices": [{"device_id": "E1", "room_id": "R1", "type": "socket"}],
        },
        "PLUMBING": {
            "discipline": "PLUMBING",
            "fixtures": [{"fixture_id": "P1", "room_id": "R1", "type": "sink"}],
            "supply_pipes": [], "drain_pipes": [],
        },
        "CEILING": {
            "discipline": "CEILING",
            "openings": [{"opening_id": "C1", "room_id": "R1", "source": "light"}],
        },
    }


def test_detects_cross_discipline_conflict():
    report = ConflictResolver().resolve(_models_with_conflict(), project_id="p1")
    assert isinstance(report, ConflictReport)
    assert report.status == "CONFLICTS_FOUND"
    assert report.conflicts
    types = {c.type for c in report.conflicts}
    # 电气×给排水 / 吊顶×电气 / 吊顶×给排水 至少各一
    assert "ELECTRICAL_x_PLUMBING" in types
    assert "CEILING_x_ELECTRICAL" in types


def test_conflict_requires_approval():
    report = ConflictResolver().resolve(_models_with_conflict(), project_id="p1")
    assert report.requires_approval is True


def test_no_conflict_when_rooms_disjoint():
    models = {
        "ELECTRICAL": {"discipline": "ELECTRICAL",
                       "devices": [{"device_id": "E1", "room_id": "R1"}]},
        "PLUMBING": {"discipline": "PLUMBING",
                     "fixtures": [{"fixture_id": "P1", "room_id": "R2"}],
                     "supply_pipes": [], "drain_pipes": []},
    }
    report = ConflictResolver().resolve(models, project_id="p1")
    assert report.status == "NO_CONFLICT"
    assert report.requires_approval is False


def test_report_serializable():
    report = ConflictResolver().resolve(_models_with_conflict(), project_id="p1")
    d = report.to_dict()
    assert d["status"] == "CONFLICTS_FOUND"
    assert d["summary"]["conflict_count"] == len(report.conflicts)
    assert "report_id" in d
