from pathlib import Path
import sys
import importlib.util


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = (
    REPO_ROOT
    / "optional-skills"
    / "communication"
    / "playwright-page-capture"
    / "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)


def test_playwright_page_capture_skill_scaffold_exists() -> None:
    root = REPO_ROOT / "optional-skills" / "communication" / "playwright-page-capture"
    assert (root / "SKILL.md").exists()
    assert (root / "scripts" / "run_page_capture.py").exists()


def test_build_browser_launch_options_includes_storage_state_when_present() -> None:
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


def test_run_capture_pipeline_returns_ok_for_baidu_poc(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "page-capture.yaml"
    config_path.write_text(
        """
        pages:
          - page_id: baidu_poc
            name: Baidu PoC
            url: https://www.baidu.com
            wait_for:
              load_state: networkidle
              selector: input[name='wd']
            network_probe:
              url_keywords: [baidu.com]
            dom_fields:
              - field: page_title
                kind: title
              - field: search_input_name
                selector: input[name='wd']
                attribute: name
            feishu_target:
              chat_id: oc_test_chat
        """,
        encoding="utf-8",
    )
    # Mock browser runner
    def mock_browser_runner(definition):
        return {
            "page": type("DummyPage", (), {
                "title": lambda self: "百度一下，你就知道",
                "query_selector": lambda self, selector: type("Node", (), {"get_attribute": lambda self, name: "wd"})(),
            })(),
            "events": [{"url": "https://www.baidu.com/api/test", "status": 200}],
            "fetch_error": None,
            "login_required": False,
        }
    # Mock feishu client
    sent = {}
    class DummyFeishuClient:
        def send_text(self, *, chat_id: str, text: str) -> str:
            sent["chat_id"] = chat_id
            sent["text"] = text
            return "om_test"

    # Load all dependencies using importlib.util first
    # Register both with and without "scripts." prefix since relative imports look for scripts.*
    for mod_name, mod_path in [
        ("page_capture_models", SCRIPTS_DIR / "page_capture_models.py"),
        ("page_capture_classify", SCRIPTS_DIR / "page_capture_classify.py"),
        ("page_capture_config", SCRIPTS_DIR / "page_capture_config.py"),
        ("page_capture_dom", SCRIPTS_DIR / "page_capture_dom.py"),
        ("page_capture_feishu", SCRIPTS_DIR / "page_capture_feishu.py"),
        ("page_capture_probe", SCRIPTS_DIR / "page_capture_probe.py"),
    ]:
        spec = importlib.util.spec_from_file_location(mod_name, mod_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        sys.modules[f"scripts.{mod_name}"] = module  # For relative import resolution
        spec.loader.exec_module(module)

    # Load run_page_capture using spec_from_file_location with package context
    run_page_capture_spec = importlib.util.spec_from_file_location(
        "run_page_capture", SCRIPTS_DIR / "run_page_capture.py"
    )
    run_page_capture_module = importlib.util.module_from_spec(run_page_capture_spec)
    # Set __package__ so relative imports work
    run_page_capture_module.__package__ = "scripts"
    sys.modules["run_page_capture"] = run_page_capture_module
    run_page_capture_spec.loader.exec_module(run_page_capture_module)

    result = run_page_capture_module.run_capture_pipeline(config_path=str(config_path), page_id="baidu_poc", feishu_client=DummyFeishuClient(), browser_runner=mock_browser_runner)
    assert result["state"] == "ok"
    assert result["message_id"] == "om_test"
    assert sent["chat_id"] == "oc_test_chat"
    assert "页面巡检结果" in sent["text"]


def test_normalize_runtime_result_returns_fetch_failed_on_navigation_error() -> None:
    # Load page_capture_browser module
    browser_spec = importlib.util.spec_from_file_location(
        "page_capture_browser", SCRIPTS_DIR / "page_capture_browser.py"
    )
    browser_module = importlib.util.module_from_spec(browser_spec)
    sys.modules["page_capture_browser"] = browser_module
    browser_spec.loader.exec_module(browser_module)

    result = browser_module.normalize_runtime_result(page=None, events=[], fetch_error="timeout", login_required=False)
    assert result["fetch_error"] == "timeout"
    assert result["login_required"] is False
    assert result["events"] == []
