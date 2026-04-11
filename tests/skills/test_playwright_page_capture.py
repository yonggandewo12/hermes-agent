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
sys.path.insert(0, SCRIPTS_DIR)


def test_playwright_page_capture_skill_scaffold_exists():
    root = Path("optional-skills/communication/playwright-page-capture")
    assert (root / "SKILL.md").exists()
    assert (root / "scripts" / "run_page_capture.py").exists()


def test_build_browser_launch_options_includes_storage_state_when_present():
    """When storage_state_path is provided, it appears in launch options."""
    # Load page_capture_models first (dependency)
    models_spec = importlib.util.spec_from_file_location(
        "page_capture_models", SCRIPTS_DIR / "page_capture_models.py"
    )
    models_module = importlib.util.module_from_spec(models_spec)
    sys.modules["page_capture_models"] = models_module
    models_spec.loader.exec_module(models_module)

    # Load page_capture_browser
    browser_spec = importlib.util.spec_from_file_location(
        "page_capture_browser", SCRIPTS_DIR / "page_capture_browser.py"
    )
    browser_module = importlib.util.module_from_spec(browser_spec)
    sys.modules["page_capture_browser"] = browser_module
    browser_spec.loader.exec_module(browser_module)

    result = browser_module.build_browser_launch_options("/tmp/state.json")
    assert result["headless"] is True
    assert result["storage_state"] == "/tmp/state.json"
