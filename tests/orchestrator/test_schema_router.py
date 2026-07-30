"""Phase 10 §8 · Schema 匹配（数据流路由）测试。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.router import SchemaRouter  # noqa: E402


def test_find_producer_and_consumer():
    router = SchemaRouter()
    producers = {c.agent_name for c in router.find_producer("LayoutModel")}
    assert "layout" in producers
    consumers = {c.agent_name for c in router.find_consumer("LayoutModel")}
    assert {"geometry", "electrical"} <= consumers


def test_route_layout_to_downstream():
    router = SchemaRouter()
    downstream = {c.agent_name for c in router.route("layout")}
    # layout 产出 LayoutModel -> geometry / 专业 Agent 均为下游
    assert {"geometry", "electrical", "lighting"} <= downstream


def test_build_flow_forms_producer_consumer_edges():
    router = SchemaRouter()
    edges = router.build_flow(["DesignSpec"])
    pairs = {(e.producer, e.consumer) for e in edges}
    assert ("layout", "geometry") in pairs
    assert ("geometry", "drawing") in pairs
    assert ("layout", "electrical") in pairs
    # 专业模型 -> validator（经 ProfessionalModels 聚合）
    assert any(e.consumer == "validator" for e in edges)


def test_professional_models_aggregate_consumed_by_validator():
    router = SchemaRouter()
    consumers = {c.agent_name for c in router.find_consumer("ElectricalModel")}
    # ElectricalModel 属专业模型，validator 通过 ProfessionalModels 聚合消费
    assert "validator" in consumers
