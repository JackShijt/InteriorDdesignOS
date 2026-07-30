"""tests.cad.test_adapter · Phase 12.6 · Adapter 接口一致性 / 注册表 / 能力系统。"""
from __future__ import annotations

import inspect

import pytest

from cad.adapter import (AutoCADAdapter, CADAdapter, CADAdapterError,
                         MockCADAdapter, available_backends, create_adapter,
                         resolve_adapter)
from cad.capability import (get_backend_capabilities, has_capability,
                            missing_capabilities, select_backend)

REQUIRED_METHODS = [
    "create_document", "create_layer", "create_entity",
    "create_dimension", "save_dwg", "load_dwg", "close",
]


class TestAdapterInterface:
    """所有后端必须实现统一的 CADAdapter 接口。"""

    @pytest.mark.parametrize("cls", [MockCADAdapter, AutoCADAdapter])
    def test_backend_implements_interface(self, cls):
        assert issubclass(cls, CADAdapter)
        for method in REQUIRED_METHODS:
            impl = getattr(cls, method, None)
            assert callable(impl), f"{cls.__name__} 缺少 {method}()"
            # 必须是覆盖后的实现而非抽象方法
            assert not getattr(impl, "__isabstractmethod__", False)

    def test_abstract_base_cannot_instantiate(self):
        with pytest.raises(TypeError):
            CADAdapter()  # type: ignore[abstract]

    @pytest.mark.parametrize("cls", [MockCADAdapter, AutoCADAdapter])
    def test_signature_consistency(self, cls):
        """子类方法签名参数须与基类一致（接口一致性）。"""
        for method in REQUIRED_METHODS:
            base_params = list(
                inspect.signature(getattr(CADAdapter, method)).parameters)
            sub_params = list(
                inspect.signature(getattr(cls, method)).parameters)
            assert sub_params[:len(base_params)] == base_params, (
                f"{cls.__name__}.{method} 签名与基类不一致")


class TestRegistry:
    def test_available_backends(self):
        assert "mock" in available_backends()
        assert "autocad" in available_backends()

    def test_create_adapter_by_name(self):
        assert isinstance(create_adapter("mock"), MockCADAdapter)
        assert isinstance(create_adapter("autocad"), AutoCADAdapter)

    def test_create_unknown_backend_raises(self):
        with pytest.raises(CADAdapterError):
            create_adapter("no_such_cad")

    def test_resolve_default_is_mock(self):
        resolved = resolve_adapter()
        assert resolved["backend"] == "mock"
        assert isinstance(resolved["adapter"], MockCADAdapter)
        assert resolved["degraded"] is False

    def test_resolve_autocad_degrades_to_mock(self):
        """AutoCAD MCP 未连接（Phase 12.3 仅接口预留）→ 自动降级 mock。"""
        resolved = resolve_adapter(preferred="autocad")
        assert resolved["backend"] == "mock"
        assert resolved["degraded"] is True
        assert isinstance(resolved["adapter"], MockCADAdapter)


class TestCapabilitySystem:
    def test_backend_capabilities_loaded(self):
        mock_caps = get_backend_capabilities("mock")
        for cap in ("line", "polyline", "dimension", "layer",
                    "save_dwg", "read_dwg"):
            assert cap in mock_caps

    def test_has_capability(self):
        assert has_capability("mock", "circle")
        assert not has_capability("autocad", "circle")

    def test_missing_capabilities(self):
        assert missing_capabilities("autocad", ["line", "circle"]) == ["circle"]

    def test_select_backend_prefers_capable(self):
        choice = select_backend(["line", "save_dwg"], preferred="autocad")
        assert choice["backend"] == "autocad"
        assert choice["degraded"] is False

    def test_select_backend_degrades_on_missing_capability(self):
        choice = select_backend(["line", "circle"], preferred="autocad")
        assert choice["backend"] == "mock"
        assert choice["degraded"] is True

    def test_select_backend_no_candidate_raises(self):
        with pytest.raises(ValueError):
            select_backend(["quantum_render"])

    def test_adapter_supports_uses_capability(self):
        adapter = MockCADAdapter()
        assert adapter.supports("circle")
        assert not adapter.supports("quantum_render")
