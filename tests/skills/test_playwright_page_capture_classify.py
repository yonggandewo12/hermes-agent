from pathlib import Path
import sys
import importlib.util


SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "optional-skills"
    / "communication"
    / "playwright-page-capture"
    / "scripts"
)


def _load_classify_module():
    spec = importlib.util.spec_from_file_location(
        "page_capture_classify", SCRIPTS_DIR / "page_capture_classify.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["page_capture_classify"] = module
    spec.loader.exec_module(module)
    return module


def test_classify_ok():
    module = _load_classify_module()
    assert module.classify_capture_result(fetch_error=None, missing_fields=[], probe_hit=True, login_required=False) == "ok"


def test_classify_field_missing():
    module = _load_classify_module()
    assert module.classify_capture_result(fetch_error=None, missing_fields=["foo"], probe_hit=True, login_required=False) == "field_missing"


def test_classify_fetch_failed():
    module = _load_classify_module()
    assert module.classify_capture_result(fetch_error="timeout", missing_fields=[], probe_hit=False, login_required=False) == "fetch_failed"


def test_classify_login_required():
    module = _load_classify_module()
    assert module.classify_capture_result(fetch_error=None, missing_fields=[], probe_hit=False, login_required=True) == "login_required"
