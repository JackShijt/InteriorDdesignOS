"""ProfessionalModel dataclass 单元测试（Phase 5 §5/§11）。"""
import sys
from dataclasses import fields
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from professional.base.professional_model import (BaseProfessionalModel,
                                                  DISCIPLINES)
from professional.electrical.electrical_model import ElectricalModel
from professional.plumbing.plumbing_model import PlumbingModel
from professional.lighting.lighting_model import LightingModel
from professional.ceiling.ceiling_model import CeilingModel
from professional.flooring.flooring_model import FlooringModel
from professional.hvac.hvac_model import HVACModel
from professional.construction.construction_model import ConstructionModel
from professional.furniture.furniture_model import FurnitureModel

EXPECTED_FIELDS = {
    ElectricalModel: ("switches", "sockets", "lights", "circuits", "panel"),
    PlumbingModel: ("water_supply", "drain", "equipment"),
    LightingModel: ("fixtures", "groups", "controls"),
    CeilingModel: ("ceiling_regions", "levels", "materials"),
    FlooringModel: ("areas", "materials", "patterns"),
    HVACModel: ("air_supply", "return_air", "equipment"),
    ConstructionModel: ("notes", "details", "specifications"),
    FurnitureModel: ("movable", "fixed", "clearance"),
}


def test_eight_models_declare_required_domain_fields():
    for cls, expected in EXPECTED_FIELDS.items():
        names = {f.name for f in fields(cls)}
        for fname in expected:
            assert fname in names, f"{cls.__name__} 缺少字段 {fname}"
        assert issubclass(cls, BaseProfessionalModel)
        assert cls.DISCIPLINE in DISCIPLINES


def test_disciplines_cover_all_eight():
    got = {cls.DISCIPLINE for cls in EXPECTED_FIELDS}
    assert got == set(DISCIPLINES)


def test_to_dict_produces_schema_shape():
    model = ElectricalModel(
        layout_model_version="v1",
        switches=[{"id": "SW-1", "room_id": "R001"}],
        panel={"id": "PANEL-1"},
        constraints=[{"type": "code", "description": "示例"}],
        quality={"confidence": 0.9, "quality_score": 90,
                 "validation_passed": True},
        metadata={"schema_version": "1.0"},
    )
    d = model.to_dict()
    for key in ("metadata", "layout_model_version", "discipline",
                "objects", "constraints", "quality"):
        assert key in d
    assert d["discipline"] == "ELECTRICAL"
    categories = {o["category"] for o in d["objects"]}
    assert categories == {"switches", "panel"}
    assert model.object_count() == 2


def test_objects_carry_category_per_collection():
    model = PlumbingModel(
        water_supply=[{"id": "WS-1"}],
        drain=[{"id": "DR-1"}, {"id": "DR-2"}],
        equipment=[],
    )
    objs = model.collect_objects()
    assert len(objs) == 3
    assert sum(1 for o in objs if o["category"] == "drain") == 2
