"""ValdoZ Webhook Event Dispatcher.

Dispatches JSON event notifications to configured endpoints on phase transitions,
approvals, gate failures, and tamper warnings.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def emit_webhook_event(
    project_root: Path,
    event_type: str,
    payload: Dict[str, Any],
    timeout_sec: int = 5,
) -> List[Dict[str, Any]]:
    """Emits an event payload to all URLs configured under 'webhooks' in .valdozrc.json.

    Returns:
        List of delivery results per endpoint.
    """
    from valdoz.packs import load_valdozrc
    valdozrc = load_valdozrc(project_root)
    webhook_urls = valdozrc.get("webhooks", [])
    if not webhook_urls:
        return []

    event_data = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project_root.name,
        "data": payload,
    }
    encoded = json.dumps(event_data).encode("utf-8")
    results = []

    for url in webhook_urls:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            results.append({"url": url, "status": "failed", "error": f"Invalid scheme '{parsed.scheme}'"})
            continue

        try:
            req = urllib.request.Request(
                url,
                data=encoded,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ValdoZ-Protocol-Engine/3.0.0",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # nosec B310
                results.append({"url": url, "status": "delivered", "code": resp.status})
        except Exception as e:
            results.append({"url": url, "status": "failed", "error": str(e)})

    return results
