#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InteriorDesignOS · Schema Validator (JSON Schema Draft 2020-12)

支持跨文件 $ref 解析：扫描 <schemas 根目录> 下所有 *.schema.json，
按其 $id 构建 referencing Registry，使 metadata / quality / room 等共享契约
可被各模型通过相对 $ref（如 "../core/metadata.schema.json"）引用
（PROJECT_RULES §4.3、SCHEMA_REFACTOR_PLAN P0-2）。

用法：
  python3 validate_schema.py <schema.json> <data.json>
  python3 validate_schema.py --schema <schema.json> --data <data.json>
  python3 validate_schema.py --schema <schema.json> --dir <examples_dir>

退出码：0 = 全部 PASS；1 = 存在 ERROR（校验失败或用法错误）。

输出：
  PASS: <data_path>
  或
  ERROR: <path> | <message>
"""

import os
import sys
import json
import glob
import argparse

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError:
    sys.stderr.write("ERROR: 缺少依赖 jsonschema/referencing，请先安装: python3 -m pip install jsonschema\n")
    sys.exit(1)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_schemas_root(schema_path):
    """向上查找名为 schemas 的目录，作为跨文件 $ref 扫描根。"""
    d = os.path.dirname(os.path.abspath(schema_path))
    while d and os.path.basename(d) != "schemas":
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent
    return d if d else None


def build_registry(schemas_root):
    """扫描 schemas 根下所有 *.schema.json，按各自 $id 注册为 Resource。"""
    resources = []
    if schemas_root and os.path.isdir(schemas_root):
        for fp in sorted(glob.glob(os.path.join(schemas_root, "**", "*.schema.json"), recursive=True)):
            try:
                doc = load_json(fp)
            except Exception:
                continue
            if not isinstance(doc, dict):
                continue
            sid = doc.get("$id")
            if not sid:
                continue
            try:
                resources.append((sid, Resource.from_contents(doc)))
            except Exception:
                continue
    if not resources:
        return Registry()
    return Registry().with_resources(resources)


def validate(schema, data, registry):
    """通过 {\"$ref\": schema.$id} 触发 registry 检索，使根文档基 URI 生效，
    从而相对 $ref（../core/metadata.schema.json 等）可正确解析。"""
    if isinstance(schema, dict) and schema.get("$id"):
        effective = {"$ref": schema["$id"]}
    else:
        effective = schema
    validator = Draft202012Validator(effective, registry=registry)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return errors


def format_error(err):
    path = ".".join(str(p) for p in err.path) or "<root>"
    return "ERROR: {} | {}".format(path, err.message)


def main(argv=None):
    ap = argparse.ArgumentParser(description="InteriorDesignOS JSON Schema Validator (Draft 2020-12)")
    ap.add_argument("schema", nargs="?", help="Schema 文件路径")
    ap.add_argument("data", nargs="?", help="待校验数据文件路径")
    ap.add_argument("--schema", dest="schema_opt", help="Schema 文件路径")
    ap.add_argument("--data", dest="data_opt", help="待校验数据文件路径")
    ap.add_argument("--dir", dest="data_dir", help="校验该目录下全部 *.json 数据文件")
    args = ap.parse_args(argv)

    schema_path = args.schema or args.schema_opt
    data_path = args.data or args.data_opt

    if not schema_path:
        sys.stderr.write("ERROR: 必须提供 schema 文件（位置参数或 --schema）\n")
        return 1
    if not os.path.isfile(schema_path):
        sys.stderr.write("ERROR: schema 文件不存在: {}\n".format(schema_path))
        return 1

    try:
        schema = load_json(schema_path)
    except Exception as e:
        sys.stderr.write("ERROR: 无法读取 schema: {}\n".format(e))
        return 1

    schemas_root = find_schemas_root(schema_path)
    registry = build_registry(schemas_root)

    if args.data_dir:
        if not os.path.isdir(args.data_dir):
            sys.stderr.write("ERROR: 目录不存在: {}\n".format(args.data_dir))
            return 1
        files = sorted(glob.glob(os.path.join(args.data_dir, "*.json")))
        if not files:
            sys.stderr.write("ERROR: 目录内无 json 文件: {}\n".format(args.data_dir))
            return 1
        overall_ok = True
        for fp in files:
            try:
                data = load_json(fp)
            except Exception as e:
                print("[FAIL] {}: 无法解析 JSON - {}".format(fp, e))
                overall_ok = False
                continue
            errors = validate(schema, data, registry)
            if not errors:
                print("PASS: {}".format(fp))
            else:
                overall_ok = False
                print("[FAIL] {}".format(fp))
                for e in errors:
                    print("  " + format_error(e))
        return 0 if overall_ok else 1

    if not data_path:
        sys.stderr.write("ERROR: 必须提供 data 文件（位置参数或 --data），或使用 --dir\n")
        return 1
    if not os.path.isfile(data_path):
        sys.stderr.write("ERROR: data 文件不存在: {}\n".format(data_path))
        return 1
    try:
        data = load_json(data_path)
    except Exception as e:
        sys.stderr.write("ERROR: 无法读取 data: {}\n".format(e))
        return 1

    errors = validate(schema, data, registry)
    if not errors:
        print("PASS: {}".format(data_path))
        return 0
    for e in errors:
        print(format_error(e))
    return 1


if __name__ == "__main__":
    sys.exit(main())
