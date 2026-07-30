"""
InteriorDesignOS · ModelConverter（Phase 5.1 §8）

统一负责 dataclass <-> dict/json 的双向转换：

    dataclass --to_dict/to_json--> dict/json 字符串
    dict/json --from_dict/from_json--> dataclass

规则：
- 禁止 Agent 自己处理 JSON 序列化细节
- 转换时忽略目标 dataclass 未声明的字段（前向兼容）
- 嵌套 dataclass / list / dict 递归处理
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Dict, Type, TypeVar, get_args, get_origin

T = TypeVar("T")


class ModelConversionError(Exception):
    """模型转换失败。"""


class ModelConverter:
    """dataclass <-> dict / json 的统一转换器（纯静态工具类）。"""

    # ------------------------------------------------------------------ #
    # dataclass -> dict / json
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_dict(model: Any) -> Dict[str, Any]:
        if not dataclasses.is_dataclass(model) or isinstance(model, type):
            raise ModelConversionError(
                f"to_dict 需要 dataclass 实例，得到 {type(model).__name__}")
        return dataclasses.asdict(
            model,
            dict_factory=lambda kv: {
                k: (str(v) if isinstance(v, Path) else v) for k, v in kv
            },
        )

    @staticmethod
    def to_json(model: Any, indent: int = 2) -> str:
        return json.dumps(ModelConverter.to_dict(model), ensure_ascii=False,
                          indent=indent, default=str)

    # ------------------------------------------------------------------ #
    # dict / json -> dataclass
    # ------------------------------------------------------------------ #
    @staticmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        if not dataclasses.is_dataclass(cls):
            raise ModelConversionError(f"{cls!r} 不是 dataclass")
        if not isinstance(data, dict):
            raise ModelConversionError(
                f"from_dict 需要 dict，得到 {type(data).__name__}")
        kwargs: Dict[str, Any] = {}
        for f in dataclasses.fields(cls):
            if f.name not in data:
                continue
            kwargs[f.name] = ModelConverter._convert_value(f.type, data[f.name])
        try:
            return cls(**kwargs)  # type: ignore[call-arg]
        except TypeError as exc:
            raise ModelConversionError(
                f"构造 {cls.__name__} 失败: {exc}") from exc

    @staticmethod
    def from_json(cls: Type[T], text: str) -> T:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ModelConversionError(f"JSON 解析失败: {exc}") from exc
        return ModelConverter.from_dict(cls, data)

    # ------------------------------------------------------------------ #
    # 递归转换
    # ------------------------------------------------------------------ #
    @staticmethod
    def _convert_value(ftype: Any, value: Any) -> Any:
        if value is None:
            return None
        # 字符串形式的类型注解无法解析时原样返回
        if isinstance(ftype, str):
            return value
        if dataclasses.is_dataclass(ftype) and isinstance(value, dict):
            return ModelConverter.from_dict(ftype, value)
        origin = get_origin(ftype)
        args = get_args(ftype)
        if origin in (list, tuple) and args:
            inner = args[0]
            converted = [ModelConverter._convert_value(inner, v) for v in value]
            return tuple(converted) if origin is tuple else converted
        if origin is dict and len(args) == 2:
            return {k: ModelConverter._convert_value(args[1], v)
                    for k, v in value.items()}
        # Optional[X] / Union
        if origin is not None and args:
            for candidate in args:
                if dataclasses.is_dataclass(candidate) and isinstance(value, dict):
                    return ModelConverter.from_dict(candidate, value)
        if ftype is Path and isinstance(value, str):
            return Path(value)
        return value


__all__ = ["ModelConverter", "ModelConversionError"]
