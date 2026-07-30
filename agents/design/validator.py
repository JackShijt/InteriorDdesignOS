"""DesignSpec 校验器（Phase 4 §9）。

复用单一 jsonschema 实例 + 全局 $ref registry，确保所有 schema 的相互引用
（core/metadata、cad/original_model 等）都能正确解析，与 Parser 校验器一致。
"""
import json
from pathlib import Path
from typing import Any, Dict, List

import referencing
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from agents.design.exceptions import ValidationError

# schema 根目录
SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"
SPEC_PATH = SCHEMA_ROOT / "design" / "design_spec.schema.json"


def _build_registry() -> Registry:
    """扫描 schemas/**/*.schema.json，按 $id 建立引用注册表（与 Parser 校验器一致）。"""
    specs: List[tuple] = []
    for p in SCHEMA_ROOT.rglob("*.schema.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        uri = data.get("$id")
        if not uri:
            continue
        specs.append((uri, data))
    reg = Registry()
    for uri, data in specs:
        resource = Resource.from_contents(
            data, default_specification=referencing.jsonschema.DRAFT202012
        )
        reg = reg.with_resource(uri, resource)
    if not specs:
        raise ValidationError("未找到任何 schema（SCHEMA_ROOT=%s）" % SCHEMA_ROOT)
    return reg


_REGISTRY: Registry = _build_registry()


def validate(spec: Dict[str, Any]) -> List[str]:
    """校验 DesignSpec，返回错误列表（空列表表示通过）。"""
    if not SPEC_PATH.exists():
        raise ValidationError("缺少 design_spec.schema.json: %s" % SPEC_PATH)
    schema = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, registry=_REGISTRY)
    errors: List[str] = []
    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors


def assert_valid(spec: Dict[str, Any]) -> None:
    """校验 DesignSpec，失败抛出 ValidationError。"""
    errors = validate(spec)
    if errors:
        raise ValidationError("DesignSpec 校验失败:\n" + "\n".join(errors))


def is_valid(spec: Dict[str, Any]) -> bool:
    return len(validate(spec)) == 0


__all__ = ["validate", "assert_valid", "is_valid", "SPEC_PATH"]
