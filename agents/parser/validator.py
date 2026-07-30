"""
InteriorDesignOS · Parser · Schema Validation（Phase 3 §6）

Parser 输出 OriginalModel 后，自动用 schemas/cad/original_model.schema.json 校验。
校验失败 -> 抛出 ValidationError，不得继续执行。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import referencing
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from agents.parser.exceptions import ValidationError


# 定位仓库 schemas 根目录（agents/parser -> repo/schemas）
_SCHEMAS_ROOT = (Path(__file__).resolve().parent.parent.parent / "schemas").resolve()
_ORIGINAL_MODEL_SCHEMA = _SCHEMAS_ROOT / "cad" / "original_model.schema.json"


def _build_registry() -> Registry:
    """扫描 schemas/**/*.schema.json，按 $id 建立引用注册表（与 validate_schema.py 一致）。"""
    specs: List[tuple[str, dict]] = []
    for path in _SCHEMAS_ROOT.rglob("*.schema.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
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
    return reg


_REGISTRY: Registry = _build_registry()


def validate_original_model(model: dict) -> List[str]:
    """校验 OriginalModel，返回错误描述列表（空列表表示通过）。"""
    schema = json.loads(_ORIGINAL_MODEL_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, registry=_REGISTRY)
    errors: List[str] = []
    for err in sorted(validator.iter_errors(model), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors


def assert_valid(model: dict) -> None:
    """校验 OriginalModel；不合法时抛出 ValidationError 并中止。"""
    errors = validate_original_model(model)
    if errors:
        raise ValidationError(
            "OriginalModel Schema 校验失败:\n" + "\n".join(f"  - {e}" for e in errors)
        )


__all__ = ["validate_original_model", "assert_valid"]
