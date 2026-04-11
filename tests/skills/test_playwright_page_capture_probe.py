from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import importlib.util


SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "optional-skills"
    / "communication"
    / "playwright-page-capture"
    / "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)


def _load_module(name: str, path: Path) -> Any:
    """Load a module from a file path and register it in sys.modules."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to create module spec for {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_probe_modules() -> tuple[Any, Any]:
    """Load page_capture_models and page_capture_probe modules."""
    models_module = _load_module(
        "page_capture_models", SCRIPTS_DIR / "page_capture_models.py"
    )
    probe_module = _load_module(
        "page_capture_probe", SCRIPTS_DIR / "page_capture_probe.py"
    )
    return models_module, probe_module


def test_probe_network_events_hits_keyword_and_status() -> None:
    _, probe_module = _load_probe_modules()

    events = [
        {"url": "https://www.baidu.com/api/test", "status": 200},
        {"url": "https://other.example.com/x", "status": 204},
    ]
    result = probe_module.probe_network_events(events, ["baidu.com"])
    assert result.hit is True
    assert result.status == 200
    assert result.url == "https://www.baidu.com/api/test"


def test_probe_network_events_no_hit() -> None:
    _, probe_module = _load_probe_modules()

    events = [
        {"url": "https://other.example.com/x", "status": 204},
    ]
    result = probe_module.probe_network_events(events, ["baidu.com"])
    assert result.hit is False
    assert result.url is None
    assert result.status is None