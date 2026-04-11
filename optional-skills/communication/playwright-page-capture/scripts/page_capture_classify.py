from __future__ import annotations

def classify_capture_result(*, fetch_error: str | None, missing_fields: list[str], probe_hit: bool, login_required: bool) -> str:
    if login_required:
        return "login_required"
    if fetch_error:
        return "fetch_failed"
    if missing_fields or not probe_hit:
        return "field_missing"
    return "ok"
