import sys
import json
from pathlib import Path
import importlib.util
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR_AUTH = REPO_ROOT / "optional-skills" / "communication" / "playwright-auth-login" / "scripts"
SCRIPTS_DIR_CAPTURE = REPO_ROOT / "optional-skills" / "communication" / "playwright-page-capture" / "scripts"

# Add both dirs to sys.path for imports
for d in [str(SCRIPTS_DIR_AUTH), str(SCRIPTS_DIR_CAPTURE)]:
    if d not in sys.path:
        sys.path.insert(0, d)


def load_auth_login_module():
    sys.path.insert(0, str(SCRIPTS_DIR_AUTH))
    sys.path.insert(0, str(SCRIPTS_DIR_CAPTURE))
    # Load capture config first (needed by auth login)
    capture_config_spec = importlib.util.spec_from_file_location("page_capture_config", SCRIPTS_DIR_CAPTURE / "page_capture_config.py")
    capture_config_module = importlib.util.module_from_spec(capture_config_spec)
    sys.modules["page_capture_config"] = capture_config_module
    capture_config_spec.loader.exec_module(capture_config_module)

    # Load auth models
    models_spec = importlib.util.spec_from_file_location("playwright_auth_models", SCRIPTS_DIR_AUTH / "playwright_auth_models.py")
    models_module = importlib.util.module_from_spec(models_spec)
    sys.modules["playwright_auth_models"] = models_module
    models_spec.loader.exec_module(models_module)

    # Load auth config
    auth_config_spec = importlib.util.spec_from_file_location("playwright_auth_config", SCRIPTS_DIR_AUTH / "playwright_auth_config.py")
    auth_config_module = importlib.util.module_from_spec(auth_config_spec)
    sys.modules["playwright_auth_config"] = auth_config_module
    auth_config_spec.loader.exec_module(auth_config_module)

    # Load auth runner
    runner_spec = importlib.util.spec_from_file_location("playwright_auth_runner", SCRIPTS_DIR_AUTH / "playwright_auth_runner.py")
    runner_module = importlib.util.module_from_spec(runner_spec)
    sys.modules["playwright_auth_runner"] = runner_module
    runner_spec.loader.exec_module(runner_module)

    # Load auth login CLI
    login_spec = importlib.util.spec_from_file_location("playwright_auth_login", SCRIPTS_DIR_AUTH / "playwright_auth_login.py")
    login_module = importlib.util.module_from_spec(login_spec)
    sys.modules["playwright_auth_login"] = login_module
    login_spec.loader.exec_module(login_module)
    return login_module


def test_run_linked_pages_filters_by_auth_site_id(tmp_path: Path):
    """run_linked_pages returns only pages matching the auth_site_id."""
    # Create capture config with two pages, only one matching
    capture_config_path = tmp_path / "playwright-page-capture.yaml"
    capture_config_path.write_text(
        """
        pages:
          - page_id: dashboard_main
            name: Dashboard Main
            url: https://example.com/dashboard
            auth_site_id: feishu_admin
            wait_for:
              load_state: networkidle
            network_probe:
              url_keywords: [example.com]
            dom_fields: []
            feishu_target:
              chat_id: oc_test_chat
          - page_id: unrelated_page
            name: Unrelated
            url: https://other.com
            wait_for:
              load_state: networkidle
            network_probe:
              url_keywords: [other.com]
            dom_fields: []
            feishu_target:
              chat_id: oc_other_chat
        """,
        encoding="utf-8",
    )

    module = load_auth_login_module()

    results = module.run_linked_pages(
        capture_config_path=str(capture_config_path),
        site_id="feishu_admin",
        storage_state_path="feishu/feishu_admin.js",
        feishu_client=object(),
        browser_runner=lambda page_def: {},
        capture_runner=lambda **kwargs: {"state": "ok", "message_id": "om_test"},
    )

    assert len(results) == 1
    assert results[0]["page_id"] == "dashboard_main"
    assert results[0]["status"] == "ok"


def test_summarize_linked_pages_counts_correctly():
    module = load_auth_login_module()

    results = [
        {"page_id": "p1", "status": "ok"},
        {"page_id": "p2", "status": "ok"},
        {"page_id": "p3", "status": "fetch_failed"},
        {"page_id": "p4", "status": "field_missing"},
        {"page_id": "p5", "status": "login_required"},
    ]
    summary = module.summarize_linked_pages(results)
    assert summary == {"total": 5, "ok": 2, "failed": 3}


def test_summarize_linked_pages_empty_returns_zeros():
    module = load_auth_login_module()
    summary = module.summarize_linked_pages([])
    assert summary == {"total": 0, "ok": 0, "failed": 0}


def test_playwright_auth_login_skill_scaffold_exists() -> None:
    """Skill scaffold: DESCRIPTION.md, SKILL.md, and CLI script must exist."""
    root = REPO_ROOT / "optional-skills" / "communication" / "playwright-auth-login"
    assert (root / "DESCRIPTION.md").exists(), "DESCRIPTION.md missing"
    assert (root / "SKILL.md").exists(), "SKILL.md missing"
    assert (root / "scripts" / "playwright_auth_login.py").exists(), "playwright_auth_login.py missing"
