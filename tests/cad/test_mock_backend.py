"""tests.cad.test_mock_backend · Phase 12.6 · Mock 后端行为 + DrawingModel 生成 CAD 实体。"""
from __future__ import annotations

import pytest

from cad.adapter import MockCADAdapter
from cad.adapter.base import DocumentNotOpenError, UnsupportedOperationError
from runtime.pipeline.cad_export import (export_drawing_to_dwg,
                                         translate_drawing_model)


def _sample_drawing_model():
    """一个最小的确定性 DrawingModel（结构与 DrawingAgent 输出一致）。"""
    return {
        "drawing_model_version": "1.0",
        "units": "mm",
        "layers": [
            {"name": "WALL", "color": "7", "line_type": "CONTINUOUS"},
            {"name": "DOOR", "color": "3", "line_type": "CONTINUOUS"},
            {"name": "WIN", "color": "5", "line_type": "CONTINUOUS"},
            {"name": "DIM", "color": "1", "line_type": "CONTINUOUS"},
        ],
        "entities": [
            {"entity_id": "W001", "type": "WALL", "layer": "WALL",
             "points": [{"x": 0, "y": 0}, {"x": 5000, "y": 0}],
             "thickness": 200},
            {"entity_id": "D001", "type": "DOOR", "layer": "DOOR",
             "start": {"x": 2050, "y": 0}, "end": {"x": 2950, "y": 0},
             "width": 900},
            {"entity_id": "WIN001", "type": "WINDOW", "layer": "WIN",
             "start": {"x": 5000, "y": 1250}, "end": {"x": 5000, "y": 2750},
             "width": 1500},
            {"entity_id": "R01-F1", "type": "FURNITURE", "layer": "FURN",
             "geometry_ref": "SOFA", "position": {"x": 2500, "y": 2000}},
        ],
        "dimensions": [
            {"dimension_id": "DIM-R01", "start": [0, 0], "end": [5000, 0],
             "value": 5000.0, "unit": "mm", "layer": "DIM"},
        ],
        "annotations": [
            {"text": "客厅", "position": {"x": 2500, "y": 2000},
             "height": 300, "layer": "AXIS"},
        ],
    }


class TestMockAdapterBasics:
    def test_document_lifecycle(self):
        adapter = MockCADAdapter()
        doc_id = adapter.create_document("demo")
        assert doc_id
        adapter.close()
        with pytest.raises(DocumentNotOpenError):
            adapter.create_layer("WALL")

    def test_draw_requires_document(self):
        adapter = MockCADAdapter()
        with pytest.raises(DocumentNotOpenError):
            adapter.create_entity({"type": "line"})

    def test_layer_dedup(self):
        adapter = MockCADAdapter()
        adapter.create_document("demo")
        adapter.create_layer("WALL")
        adapter.create_layer("WALL")
        assert len(adapter._doc["layers"]) == 1  # noqa: SLF001

    def test_unsupported_entity_type(self):
        adapter = MockCADAdapter()
        adapter.create_document("demo")
        with pytest.raises(UnsupportedOperationError):
            adapter.create_entity({"type": "nurbs_surface"})

    def test_entities_get_unique_ids(self):
        adapter = MockCADAdapter()
        adapter.create_document("demo")
        e1 = adapter.create_entity({"type": "line",
                                    "start": {"x": 0, "y": 0},
                                    "end": {"x": 1, "y": 1}})
        e2 = adapter.create_entity({"type": "line",
                                    "start": {"x": 1, "y": 1},
                                    "end": {"x": 2, "y": 2}})
        assert e1 != e2


class TestDrawingModelTranslation:
    """DrawingModel 可生成 CAD 实体（后端中性）。"""

    def test_translate_entities(self):
        neutral = translate_drawing_model(_sample_drawing_model())
        types = sorted(e["type"] for e in neutral["entities"])
        assert types == ["block", "line", "line", "polyline", "text"]
        roles = {e.get("role") for e in neutral["entities"]}
        assert {"wall", "door", "window", "furniture", "annotation"} <= roles
        assert len(neutral["dimensions"]) == 1
        assert len(neutral["layers"]) == 4

    def test_tags_preserved(self):
        neutral = translate_drawing_model(_sample_drawing_model())
        tags = {e.get("tag") for e in neutral["entities"]}
        assert {"W001", "D001", "WIN001", "R01-F1"} <= tags


class TestMockExport:
    def test_export_generates_dwg(self, tmp_path):
        dwg = tmp_path / "demo.dwg"
        report = export_drawing_to_dwg(_sample_drawing_model(), str(dwg),
                                       project_id="demo",
                                       preferred_backend="mock")
        assert report["backend"] == "mock"
        assert dwg.exists()
        assert report["dimension_count"] == 1
        assert report["skipped"] == []

    def test_dwg_readable_after_export(self, tmp_path):
        dwg = tmp_path / "demo.dwg"
        export_drawing_to_dwg(_sample_drawing_model(), str(dwg),
                              project_id="demo", preferred_backend="mock")
        adapter = MockCADAdapter()
        data = adapter.load_dwg(str(dwg))
        assert len(data["entities"]) == 5
        assert len(data["dimensions"]) == 1
        assert {l["name"] for l in data["layers"]} == {"WALL", "DOOR",
                                                       "WIN", "DIM"}
