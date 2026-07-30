"""
Phase 5.1 §11 · import_dependency_test

架构约束（docs/PROFESSIONAL_FRAMEWORK.md · Dependency Rules）：

    Runtime -> Orchestrator -> Agent -> RuleEngine -> Model

- professional/ 禁止 import runtime / orchestrator / agents.orchestrator
- core/ 禁止 import runtime / orchestrator / professional / agents（最底层）
- models/ 禁止 import runtime / orchestrator / professional / agents
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

# 包 -> 禁止依赖的顶级包前缀
FORBIDDEN = {
    "professional": ("runtime", "orchestrator", "agents"),
    "cad": ("runtime", "orchestrator", "agents", "professional"),
    "core": ("runtime", "orchestrator", "agents", "professional"),
    "models": ("runtime", "orchestrator", "agents", "professional"),
}


def _iter_imports(pyfile: Path) -> Iterator[str]:
    tree = ast.parse(pyfile.read_text(encoding="utf-8"), filename=str(pyfile))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                yield node.module


def _violations(package: str, forbidden: Tuple[str, ...]) -> List[str]:
    violations: List[str] = []
    pkg_dir = REPO_ROOT / package
    for pyfile in sorted(pkg_dir.rglob("*.py")):
        for module in _iter_imports(pyfile):
            top = module.split(".")[0]
            if top in forbidden:
                violations.append(
                    f"{pyfile.relative_to(REPO_ROOT)} -> import {module}")
    return violations


def test_professional_must_not_import_runtime_or_orchestrator():
    violations = _violations("professional", FORBIDDEN["professional"])
    assert not violations, (
        "professional/ 出现禁止依赖（Phase 5.1 §2）：\n" + "\n".join(violations))


def test_core_must_not_import_upper_layers():
    violations = _violations("core", FORBIDDEN["core"])
    assert not violations, (
        "core/ 作为最底层禁止反向依赖：\n" + "\n".join(violations))


def test_cad_must_not_import_upper_layers():
    violations = _violations("cad", FORBIDDEN["cad"])
    assert not violations, (
        "cad/ 禁止反向依赖 runtime/orchestrator/agents/professional：\n"
        + "\n".join(violations))


def test_models_must_not_import_upper_layers():
    violations = _violations("models", FORBIDDEN["models"])
    assert not violations, (
        "models/ 禁止反向依赖：\n" + "\n".join(violations))
