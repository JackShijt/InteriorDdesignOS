"""Phase 3.5 §5 Agent Registry 测试。"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime.agent_registry import (build_runtime_registry, PLACEHOLDER_AGENTS,
                                     PARSER_AGENT)
from agents.parser.parser import ParserAgent


def test_registry_has_parser_and_placeholders():
    reg = build_runtime_registry()
    assert PARSER_AGENT in reg.names()
    for name in PLACEHOLDER_AGENTS:
        assert name in reg.names(), name


def test_registry_parser_is_real():
    reg = build_runtime_registry()
    agent = reg.get("parser")
    assert isinstance(agent, ParserAgent)
    assert agent.agent_name == "parser"


def test_registry_get_unknown_returns_none():
    reg = build_runtime_registry()
    assert reg.get("nonexistent") is None
