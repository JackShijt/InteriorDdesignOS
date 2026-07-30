"""
InteriorDesignOS · Professional Validator（Phase 5 §9）

Professional Validation 聚合校验：
1. Schema 合法：每个 ProfessionalModel 符合
   schemas/professional/professional_model.schema.json
2. 版本一致：所有 ProfessionalModel 的 metadata.schema_version 一致
3. LayoutVersion 一致：所有 layout_model_version 相同，
   且（若提供 LayoutModel）与 layout.version.model_version 一致
4. Quality 合法：quality 数值域合法且 validation_passed 为 True

只做校验与聚合报告，不修改任何模型（SRP）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from core import REPO_ROOT

logger = logging.getLogger(__name__)

_SCHEMA_PATH = (REPO_ROOT / "schemas" / "professional"
                / "professional_model.schema.json")
_SCHEMAS_ROOT = REPO_ROOT / "schemas"

_validator_cache: Optional[Draft202012Validator] = None


class ProfessionalValidationError(Exception):
    """ProfessionalModel 校验失败（阻断落盘）。"""


def _build_validator() -> Draft202012Validator:
    """扫描 schemas/ 下全部 *.schema.json 构建跨文件 $ref Registry。"""
    global _validator_cache
    if _validator_cache is not None:
        return _validator_cache
    resources = []
    for fp in sorted(_SCHEMAS_ROOT.rglob("*.schema.json")):
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sid = doc.get("$id") if isinstance(doc, dict) else None
        if sid:
            resources.append((sid, Resource.from_contents(doc)))
    registry = Registry().with_resources(resources)
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    effective = {"$ref": schema["$id"]} if schema.get("$id") else schema
    _validator_cache = Draft202012Validator(effective, registry=registry)
    return _validator_cache


# ================= 单模型校验 =================
def validate_model(model: Dict[str, Any]) -> List[str]:
    """Schema 校验单个 ProfessionalModel，返回错误列表（空 = 通过）。"""
    validator = _build_validator()
    errors = sorted(validator.iter_errors(model), key=lambda e: list(e.path))
    return [
        f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
        for e in errors
    ]


def assert_model_valid(model: Dict[str, Any]) -> None:
    """校验失败抛出 ProfessionalValidationError。"""
    errs = validate_model(model)
    if errs:
        raise ProfessionalValidationError(
            "ProfessionalModel schema 校验失败: " + "; ".join(errs[:5]))


def validate_quality(model: Dict[str, Any]) -> List[str]:
    """校验 quality 合法性（数值域 + validation_passed）。"""
    errs: List[str] = []
    q = model.get("quality") or {}
    conf = q.get("confidence")
    score = q.get("quality_score")
    if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
        errs.append("quality.confidence 必须在 [0,1]")
    if not isinstance(score, (int, float)) or not 0 <= score <= 100:
        errs.append("quality.quality_score 必须在 [0,100]")
    if q.get("validation_passed") is not True:
        errs.append("quality.validation_passed 必须为 True")
    return errs


# ================= 聚合校验（Fan-in 后）=================
class ProfessionalValidator:
    """多专业聚合校验器（Phase 5 §9）。"""

    def validate_all(self, models: List[Dict[str, Any]],
                     layout: Optional[Dict[str, Any]] = None
                     ) -> Dict[str, Any]:
        """聚合校验全部 ProfessionalModel，返回校验报告（不抛异常）。"""
        per_discipline: Dict[str, List[str]] = {}
        layout_versions: Dict[str, str] = {}
        schema_versions: Dict[str, str] = {}

        for model in models:
            discipline = str(model.get("discipline", "UNKNOWN"))
            errs = validate_model(model) + validate_quality(model)
            per_discipline[discipline] = errs
            layout_versions[discipline] = str(
                model.get("layout_model_version", ""))
            schema_versions[discipline] = str(
                (model.get("metadata") or {}).get("schema_version", ""))

        version_errors = self._check_versions(layout_versions,
                                              schema_versions, layout)
        passed = (not version_errors
                  and all(not v for v in per_discipline.values())
                  and bool(models))
        report = {
            "passed": passed,
            "checked": len(models),
            "disciplines": sorted(per_discipline),
            "errors": {k: v for k, v in per_discipline.items() if v},
            "version_errors": version_errors,
            "layout_model_versions": layout_versions,
            "timestamp": datetime.now().astimezone().isoformat(),
        }
        logger.info("professional validation finished: passed=%s checked=%d",
                    passed, len(models))
        return report

    def _check_versions(self, layout_versions: Dict[str, str],
                        schema_versions: Dict[str, str],
                        layout: Optional[Dict[str, Any]]) -> List[str]:
        errs: List[str] = []
        lv = set(layout_versions.values())
        if len(lv) > 1:
            errs.append(f"layout_model_version 不一致: {layout_versions}")
        if layout is not None and lv:
            expected = (layout.get("version") or {}).get("model_version", "")
            actual = next(iter(lv))
            if len(lv) == 1 and actual != expected:
                errs.append(
                    f"layout_model_version={actual} 与 LayoutModel "
                    f"version.model_version={expected} 不一致")
        sv = set(schema_versions.values())
        if len(sv) > 1:
            errs.append(f"metadata.schema_version 不一致: {schema_versions}")
        return errs


def validate_models(models: List[Dict[str, Any]],
                    layout: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """便捷函数：聚合校验并返回报告。"""
    return ProfessionalValidator().validate_all(models, layout)


def load_and_validate_dir(professional_dir: Path,
                          layout: Optional[Dict[str, Any]] = None
                          ) -> Dict[str, Any]:
    """读取目录下全部 *_model.json 并聚合校验（Export 前使用）。"""
    models = []
    for fp in sorted(Path(professional_dir).glob("*_model.json")):
        models.append(json.loads(fp.read_text(encoding="utf-8")))
    return validate_models(models, layout)


__all__ = [
    "ProfessionalValidator", "ProfessionalValidationError",
    "validate_model", "assert_model_valid", "validate_quality",
    "validate_models", "load_and_validate_dir",
]
