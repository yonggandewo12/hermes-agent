import sys
from pathlib import Path
import importlib.util
import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "optional-skills"
    / "communication"
    / "playwright-auth-login"
    / "scripts"
)

def load_module():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("playwright_auth_config", SCRIPTS_DIR / "playwright_auth_config.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_playwright_auth_config_reads_site_definition(tmp_path: Path):
    config_path = tmp_path / "playwright-auth.yaml"
    config_path.write_text(
        """
        sites:
          - site_id: feishu_admin
            name: Feishu Admin
            login_url: https://example.com/login
            username: demo_user
            password: demo_pass
            storage_state_path: feishu/feishu_admin.js
            steps:
              - action: fill
                selector: "input[name='username']"
                value_from: username
            success_criteria:
              url_not_contains: ["/login"]
        """,
        encoding="utf-8",
    )

    module = load_module()
    config = module.load_playwright_auth_config(config_path)

    site = config.sites[0]
    assert site.site_id == "feishu_admin"
    assert site.steps[0].value_from == "username"
    assert site.success_criteria.url_not_contains == ["/login"]


def test_load_playwright_auth_config_rejects_missing_credentials(tmp_path: Path):
    config_path = tmp_path / "playwright-auth.yaml"
    config_path.write_text(
        """
        sites:
          - site_id: broken
            name: Broken
            login_url: https://example.com/login
            username: demo_user
            storage_state_path: broken.js
            steps: []
            success_criteria: {}
        """,
        encoding="utf-8",
    )

    module = load_module()
    with pytest.raises(KeyError, match="password"):
        module.load_playwright_auth_config(config_path)
