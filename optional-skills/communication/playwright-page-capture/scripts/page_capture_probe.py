from __future__ import annotations

try:
    from .page_capture_models import NetworkProbeResult
except ImportError:
    from page_capture_models import NetworkProbeResult


def probe_network_events(events: list[dict[str, object]], url_keywords: list[str]) -> NetworkProbeResult:
    for event in events:
        url = str(event.get("url") or "")
        if any(keyword in url for keyword in url_keywords):
            return NetworkProbeResult(
                hit=True,
                url=url,
                status=int(event.get("status")) if event.get("status") is not None else None,
            )
    return NetworkProbeResult(hit=False, url=None, status=None)
