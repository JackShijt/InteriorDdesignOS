"""Phase 7 §7 · CAD 依赖架构约束测试。

强制保证依赖方向（唯一允许的访问链）：
    CADSession → CADAdapter（抽象）
                        ↑
                  AutoCADAdapter（具体后端，插件加载）
                        → MCPClient → AutoCAD MCP → AutoCAD

禁止：
- agents/* 直接 import cad.autocad / autocad_adapter（Agent 不得调用 AutoCAD）
- runtime/* 直接 import cad.autocad / autocad_adapter
允许：
- cad/autocad 继承 cad/base/cad_adapter.CADAdapter
- cad/__init__ 通过插件注册表加载 autocad（同包内引用，合法）
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator, List

REPO_ROOT = Path(__file__).resolve().parents[2]

# 具体 AutoCAD 后端在 import 层面必须被隔离的模块路径前缀
AUTOCAD_FORBIDDEN_MODULES = ("cad.autocad", "cad.autocad.autocad_adapter")


def _iter_modules(pyfile: Path) -> Iterator[str]:
    """遍历文件 import，相对 import 解析为绝对模块名。"""
    tree = ast.parse(pyfile.read_text(encoding="utf-8"), filename=str(pyfile))
    rel = pyfile.relative_to(REPO_ROOT)
    parts = list(rel.with_suffix("").parts)
    pkg_parts = parts[:-1]  # 文件所属包（去掉文件名 / __init__）
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level == 0:
                if mod:
                    yield mod
            else:
                # 相对 import：base = pkg 往上 (level-1) 层
                cut = max(len(pkg_parts) - (node.level - 1), 0)
                base_parts = pkg_parts[:cut]
                if mod:
                    yield ".".join(base_parts + mod.split("."))
                else:
                    yield ".".join(base_parts)


def _violations(package: str) -> List[str]:
    violations: List[str] = []
    pkg_dir = REPO_ROOT / package
    for pyfile in sorted(pkg_dir.rglob("*.py")):
        for module in _iter_modules(pyfile):
            top = module.split(".")[0]
            if top != "cad":
                continue
            if module in AUTOCAD_FORBIDDEN_MODULES or \
                    module.startswith("cad.autocad"):
                violations.append(
                    f"{pyfile.relative_to(REPO_ROOT)} -> import {module}")
    return violations


def test_agents_must_not_import_autocad_adapter():
    violations = _violations("agents")
    assert not violations, (
        "agents/ 不得直接 import cad.autocad（Phase 7 §7）：\n"
        + "\n".join(violations))


def test_runtime_must_not_import_autocad_adapter():
    violations = _violations("runtime")
    assert not violations, (
        "runtime/ 不得直接 import cad.autocad（Phase 7 §7）：\n"
        + "\n".join(violations))


def test_cad_session_depends_on_abstract_adapter_only():
    """CADSession 必须依赖抽象 CADAdapter，且不得直接依赖 autocad_adapter。"""
    f = REPO_ROOT / "cad" / "base" / "cad_session.py"
    modules = list(_iter_modules(f))
    assert "cad.base.cad_adapter" in modules, "CADSession 应依赖 CADAdapter"
    assert "cad.autocad" not in modules, "CADSession 不得依赖具体 AutoCAD 后端"


def test_autocad_adapter_inherits_abstract_adapter():
    """允许的方向：autocad_adapter 继承 cad.base.cad_adapter.CADAdapter。"""
    f = REPO_ROOT / "cad" / "autocad" / "autocad_adapter.py"
    modules = list(_iter_modules(f))
    assert "cad.base.cad_adapter" in modules, \
        "AutoCADAdapter 应继承抽象 CADAdapter"

    src = f.read_text(encoding="utf-8")
    tree = ast.parse(src)
    bases = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AutoCADAdapter":
            for base in node.bases:
                if isinstance(base, ast.Attribute):
                    bases.append(base.attr)
                elif isinstance(base, ast.Name):
                    bases.append(base.id)
    assert "CADAdapter" in bases, "AutoCADAdapter 必须继承 CADAdapter"


def test_cad_mcp_does_not_import_upper_layers():
    """MCP Client Layer 不得依赖 agent / runtime（保持可独立复用）。"""
    violations: List[str] = []
    for pyfile in sorted((REPO_ROOT / "cad" / "mcp").rglob("*.py")):
        for module in _iter_modules(pyfile):
            top = module.split(".")[0]
            if top in ("agents", "runtime", "orchestrator"):
                violations.append(
                    f"{pyfile.relative_to(REPO_ROOT)} -> import {module}")
    assert not violations, (
        "cad/mcp 不得依赖 agents/runtime/orchestrator：\n"
        + "\n".join(violations))
