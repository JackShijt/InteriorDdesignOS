"""
Phase 3.5 §12 统一运行时配置读取。

- 所有 Runtime 配置集中读取，禁止硬编码。
- 支持 config/runtime.yaml（优先 pyyaml，缺失时退化为内置扁平解析）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from runtime import REPO_ROOT

DEFAULTS: Dict[str, Any] = {
    "workspace_path": "workspace",
    "log_level": "INFO",
    "checkpoint_interval": 1,
    "schema_validation": True,
    "auto_save": True,
    "max_retry": 2,
    # Phase 7 §四：CAD 后端选择 / AutoCAD MCP 连接参数（嵌套结构）
    "cad": {"backend": "mock"},
    "autocad": {"host": None, "port": None, "timeout": 30},
}


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    return p


def _coerce(v: str) -> Any:
    s = v.strip()
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if s.lstrip("-").isdigit():
        return int(s)
    return s


def _deep_set(d: Dict[str, Any], keys: List[str], value: Any) -> None:
    """按嵌套键路径写入 dict，如 ['cad', 'backend'] -> d['cad']['backend']。"""
    for key in keys[:-1]:
        nxt = d.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            d[key] = nxt
        d = nxt
    d[keys[-1]] = value


def _parse_simple(text: str) -> Dict[str, Any]:
    """极简 YAML 解析：支持 `key: value` 与嵌套 `a.b: value`，
    忽略 `#` 注释与空行（pyyaml 缺失时的退路）。"""
    out: Dict[str, Any] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if ":" not in s:
            continue
        k, _, v = s.partition(":")
        _deep_set(out, k.strip().split("."), _coerce(v))
    return out


def load_runtime_config(path: str | None = None) -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    p = Path(path) if path else (REPO_ROOT / "config" / "runtime.yaml")
    if p.exists():
        try:
            import yaml  # type: ignore

            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            cfg.update(data)
        except Exception:
            cfg.update(_parse_simple(p.read_text(encoding="utf-8")))
    cfg["workspace_root"] = _resolve(str(cfg["workspace_path"]))
    return cfg


__all__ = ["DEFAULTS", "load_runtime_config"]
