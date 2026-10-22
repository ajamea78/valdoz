"""ValdoZ SDK Bridge for Google Antigravity.

Enables programmatic interaction between ValdoZ Protocol and the official
google-antigravity Python SDK:
- Native tool registration (valdoz_gate_check, valdoz_slice_done, valdoz_research_log)
- Local FreeLLMAPI endpoint routing configuration
- Runtime status inspection
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


def is_sdk_available() -> bool:
    """Checks if google.antigravity is installed and importable."""
    return importlib.util.find_spec("google.antigravity") is not None


def get_sdk_version() -> Optional[str]:
    """Returns the installed google-antigravity version if available."""
    try:
        from importlib.metadata import version
        return version("google-antigravity")
    except Exception:
        return None


def get_valdoz_native_tools() -> List[Dict[str, Any]]:
    """Returns tool schemas compatible with google.antigravity agent tool registration."""
    return [
        {
            "name": "valdoz_gate_check",
            "description": "Runs ValdoZ deliverable, placeholder, and heading checks for the current phase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phase": {
                        "type": "integer",
                        "description": "Optional phase number to audit (defaults to current phase).",
                    },
                },
            },
        },
        {
            "name": "valdoz_slice_done",
            "description": "Submits a Phase 6 build slice for gate condition verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slice_id": {
                        "type": "string",
                        "description": "Identifier of the slice (e.g., '01-user-auth').",
                    },
                    "coverage_delta": {
                        "type": "number",
                        "description": "Test coverage delta percentage compared to baseline.",
                        "default": 0.0,
                    },
                },
                "required": ["slice_id"],
            },
        },
        {
            "name": "valdoz_research_log",
            "description": "Pre-logs intent to fetch an external URL before web access (Gap 4 security defense).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The external web URL to fetch.",
                    },
                    "claim": {
                        "type": "string",
                        "description": "The topic, finding, or claim expected from this source.",
                    },
                },
                "required": ["url", "claim"],
            },
        },
    ]


class FreeLLMAPIConfig(BaseModel):
    base_url: str = "http://localhost:8000/v1"
    model_name: str = "gemini-2.5-flash"
    api_key: str = "freellmapi-local"


def generate_freellmapi_config(base_url: str = "http://localhost:8000/v1") -> FreeLLMAPIConfig:
    """Generates FreeLLMAPI connection configuration for local testing."""
    return FreeLLMAPIConfig(base_url=base_url)
