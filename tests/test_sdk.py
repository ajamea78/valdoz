"""Unit tests for ValdoZ Google Antigravity SDK bridge and FreeLLMAPI configuration."""

import pytest
from valdoz.sdk_bridge import (
    is_sdk_available,
    get_sdk_version,
    get_valdoz_native_tools,
    generate_freellmapi_config,
)


def test_sdk_availability_and_version():
    avail = is_sdk_available()
    assert isinstance(avail, bool)
    version = get_sdk_version()
    if avail:
        assert version is not None
        assert version.startswith("0.1.")
    else:
        assert version is None


def test_valdoz_native_tools_declaration():
    tools = get_valdoz_native_tools()
    assert len(tools) == 3
    tool_names = [t["name"] for t in tools]
    assert "valdoz_gate_check" in tool_names
    assert "valdoz_slice_done" in tool_names
    assert "valdoz_research_log" in tool_names

    # Check schemas
    gate_tool = next(t for t in tools if t["name"] == "valdoz_gate_check")
    assert "parameters" in gate_tool
    assert "phase" in gate_tool["parameters"]["properties"]


def test_freellmapi_config_generation():
    cfg = generate_freellmapi_config("http://127.0.0.1:8000/v1")
    assert cfg.base_url == "http://127.0.0.1:8000/v1"
    assert cfg.api_key == "freellmapi-local"
