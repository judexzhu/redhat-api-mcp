import pytest

from redhat_api_mcp.server import _load_prompt


def test_load_summarize_case_prompt():
    result = _load_prompt("summarize_case", case_number="01234567")
    assert "01234567" in result
    assert "C.A.S.E. Update" in result


def test_load_resolve_case_prompt():
    result = _load_prompt("resolve_case", case_number="01234567")
    assert "01234567" in result
    assert "Investigation Workflow" in result


def test_load_resolve_case_v2_prompt():
    result = _load_prompt("resolve_case_v2", case_number="01234567")
    assert "01234567" in result
    assert "Agent Role and Goal" in result
