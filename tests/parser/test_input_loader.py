"""Input Loader 测试（Phase 3 §3 / §13）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.parser.input_loader import load_input
from agents.parser.exceptions import FatalError
from agents.parser.input_detector import InputType

EXAMPLES = Path(__file__).resolve().parent.parent.parent / "examples" / "input"


def test_load_existing_file():
    li = load_input(EXAMPLES / "sample_json" / "sample.json")
    assert li.exists
    assert li.size_bytes > 0
    assert len(li.file_hash) == 64
    assert li.input_type is InputType.TEXT
    assert li.mime_type == "application/json"


def test_load_empty_file():
    li = load_input(EXAMPLES / "empty_project" / "empty.txt")
    assert li.exists
    assert li.size_bytes == 0
    assert li.input_type is InputType.TEXT  # .txt


def test_missing_file_raises():
    try:
        load_input(EXAMPLES / "does_not_exist.dwg")
        raise AssertionError("应抛出 FatalError")
    except FatalError:
        pass
