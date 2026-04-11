from __future__ import annotations


def build_browser_launch_options(storage_state_path: str | None) -> dict[str, object]:
    return {
        "headless": True,
        "storage_state": storage_state_path,
    }


def run_browser_capture(page_def):
    raise NotImplementedError("Wire browser runner in implementation task")