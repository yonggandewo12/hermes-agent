from pathlib import Path
import sys
import importlib.util
import types

import pytest


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


def test_run_capture_pipeline_prefers_config_feishu_credentials(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "page-capture.yaml"
    config_path.write_text(
        """
        feishu:
          app_id: cli_from_config
          app_secret: secret_from_config
        pages:
          - page_id: baidu_poc
            name: Baidu PoC
            url: https://www.baidu.com
            wait_for:
              load_state: networkidle
            network_probe:
              url_keywords: [baidu.com]
            dom_fields:
              - field: page_title
                kind: title
            feishu_target:
              chat_id: oc_test_chat
        """,
        encoding="utf-8",
    )

    monkeypatch.setenv("FEISHU_APP_ID", "env_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "env_secret")

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
        sys.modules[f"scripts.{mod_name}"] = module
        spec.loader.exec_module(module)

    run_page_capture_spec = importlib.util.spec_from_file_location(
        "run_page_capture", SCRIPTS_DIR / "run_page_capture.py"
    )
    run_page_capture_module = importlib.util.module_from_spec(run_page_capture_spec)
    run_page_capture_module.__package__ = "scripts"
    sys.modules["run_page_capture"] = run_page_capture_module
    run_page_capture_spec.loader.exec_module(run_page_capture_module)

    captured = {}

    class DummyFeishuClient:
        def __init__(self, *, app_id: str, app_secret: str):
            captured["app_id"] = app_id
            captured["app_secret"] = app_secret

        def send_text(self, *, chat_id: str, text: str) -> str:
            return "om_test"

    monkeypatch.setattr(run_page_capture_module, "FeishuAppClient", DummyFeishuClient)

    client = run_page_capture_module.build_feishu_client(str(config_path))

    assert captured == {"app_id": "cli_from_config", "app_secret": "secret_from_config"}
    assert client is not None


def test_run_capture_pipeline_skips_dom_extraction_when_fetch_fails(tmp_path: Path) -> None:
    config_path = tmp_path / "page-capture.yaml"
    config_path.write_text(
        """
        pages:
          - page_id: baidu_poc
            name: Baidu PoC
            url: https://www.baidu.com
            wait_for:
              load_state: networkidle
            network_probe:
              url_keywords: [baidu.com]
            dom_fields:
              - field: page_title
                kind: title
            feishu_target:
              chat_id: oc_test_chat
        """,
        encoding="utf-8",
    )

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
        sys.modules[f"scripts.{mod_name}"] = module
        spec.loader.exec_module(module)

    run_page_capture_spec = importlib.util.spec_from_file_location(
        "run_page_capture", SCRIPTS_DIR / "run_page_capture.py"
    )
    run_page_capture_module = importlib.util.module_from_spec(run_page_capture_spec)
    run_page_capture_module.__package__ = "scripts"
    sys.modules["run_page_capture"] = run_page_capture_module
    run_page_capture_spec.loader.exec_module(run_page_capture_module)

    class DummyFeishuClient:
        def send_text(self, *, chat_id: str, text: str) -> str:
            assert chat_id == "oc_test_chat"
            assert "fetch_failed" in text
            return "om_failed"

    result = run_page_capture_module.run_capture_pipeline(
        config_path=str(config_path),
        page_id="baidu_poc",
        feishu_client=DummyFeishuClient(),
        browser_runner=lambda definition: {
            "page": None,
            "events": [],
            "fetch_error": "timeout",
            "login_required": False,
        },
    )

    assert result["state"] == "fetch_failed"
    assert result["message_id"] == "om_failed"


def test_normalize_runtime_result_returns_fetch_failed_on_navigation_error() -> None:
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


def test_build_feishu_client_uses_hermes_global_config(monkeypatch, tmp_path: Path) -> None:
    """Priority 2: falls back to Hermes global config when page-capture config has no feishu."""
    config_path = tmp_path / "page-capture.yaml"
    config_path.write_text(
        """
        pages:
          - page_id: baidu_poc
            name: Baidu PoC
            url: https://www.baidu.com
            wait_for:
              load_state: networkidle
            network_probe:
              url_keywords: [baidu.com]
            dom_fields: []
            feishu_target:
              chat_id: oc_test_chat
        """,
        encoding="utf-8",
    )

    captured = {}

    class DummyFeishuClient:
        def __init__(self, *, app_id: str, app_secret: str):
            captured["app_id"] = app_id
            captured["app_secret"] = app_secret

        def send_text(self, *, chat_id: str, text: str) -> str:
            return "om_test"

    # Mock hermes global config
    class DummyHermesConfig(dict):
        def get(self, key, default=None):
            if key == "tools":
                return {"playwright_page_capture": {"feishu": {"app_id": "hermes_app", "app_secret": "hermes_secret"}}}
            return super().get(key, default)

    # Load run_page_capture with fresh modules
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
        sys.modules[f"scripts.{mod_name}"] = module
        spec.loader.exec_module(module)

    run_page_capture_spec = importlib.util.spec_from_file_location(
        "run_page_capture", SCRIPTS_DIR / "run_page_capture.py"
    )
    run_page_capture_module = importlib.util.module_from_spec(run_page_capture_spec)
    run_page_capture_module.__package__ = "scripts"
    sys.modules["run_page_capture"] = run_page_capture_module
    run_page_capture_spec.loader.exec_module(run_page_capture_module)

    monkeypatch.setattr(run_page_capture_module, "FeishuAppClient", DummyFeishuClient)
    # Ensure hermes_cli.config is loaded before patching
    import hermes_cli.config as hc_config
    monkeypatch.setattr(hc_config, "load_config", lambda: DummyHermesConfig({
        "tools": {"playwright_page_capture": {"feishu": {"app_id": "hermes_app", "app_secret": "hermes_secret"}}}
    }))

    client = run_page_capture_module.build_feishu_client(str(config_path))
    assert captured == {"app_id": "hermes_app", "app_secret": "hermes_secret"}


def test_build_feishu_client_uses_env_vars_when_no_config(monkeypatch, tmp_path: Path) -> None:
    """Priority 3: falls back to env vars when no config has feishu credentials."""
    config_path = tmp_path / "page-capture.yaml"
    config_path.write_text(
        """
        pages:
          - page_id: baidu_poc
            name: Baidu PoC
            url: https://www.baidu.com
            wait_for:
              load_state: networkidle
            network_probe:
              url_keywords: [baidu.com]
            dom_fields: []
            feishu_target:
              chat_id: oc_test_chat
        """,
        encoding="utf-8",
    )

    captured = {}

    class DummyFeishuClient:
        def __init__(self, *, app_id: str, app_secret: str):
            captured["app_id"] = app_id
            captured["app_secret"] = app_secret

        def send_text(self, *, chat_id: str, text: str) -> str:
            return "om_test"

    class DummyHermesConfig(dict):
        def get(self, key, default=None):
            return super().get(key, default)

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
        sys.modules[f"scripts.{mod_name}"] = module
        spec.loader.exec_module(module)

    run_page_capture_spec = importlib.util.spec_from_file_location(
        "run_page_capture", SCRIPTS_DIR / "run_page_capture.py"
    )
    run_page_capture_module = importlib.util.module_from_spec(run_page_capture_spec)
    run_page_capture_module.__package__ = "scripts"
    sys.modules["run_page_capture"] = run_page_capture_module
    run_page_capture_spec.loader.exec_module(run_page_capture_module)

    monkeypatch.setattr(run_page_capture_module, "FeishuAppClient", DummyFeishuClient)
    import hermes_cli.config as hc_config
    monkeypatch.setattr(hc_config, "load_config", lambda: DummyHermesConfig({}))
    monkeypatch.setenv("FEISHU_APP_ID", "env_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "env_secret")

    client = run_page_capture_module.build_feishu_client(str(config_path))
    assert captured == {"app_id": "env_app", "app_secret": "env_secret"}


def test_main_uses_default_config_path(monkeypatch, tmp_path: Path) -> None:
    """When --config is omitted, script uses the path from _default_config_path()."""
    config_file = tmp_path / "page-capture.yaml"
    config_file.write_text(
        """
        feishu:
          app_id: default_app_id
          app_secret: default_app_secret
        pages:
          - page_id: baidu_poc
            name: Baidu PoC
            url: https://www.baidu.com
            wait_for:
              load_state: networkidle
            network_probe:
              url_keywords: [baidu.com]
            dom_fields: []
            feishu_target:
              chat_id: oc_test_chat
        """,
        encoding="utf-8",
    )

    captured = {}

    class DummyFeishuClient:
        def __init__(self, *, app_id: str, app_secret: str):
            captured["app_id"] = app_id
            captured["app_secret"] = app_secret

        def send_text(self, *, chat_id: str, text: str) -> str:
            return "om_test"

    class DummyBrowserResult(dict):
        pass

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
        sys.modules[f"scripts.{mod_name}"] = module
        spec.loader.exec_module(module)

    run_page_capture_spec = importlib.util.spec_from_file_location(
        "run_page_capture", SCRIPTS_DIR / "run_page_capture.py"
    )
    run_page_capture_module = importlib.util.module_from_spec(run_page_capture_spec)
    run_page_capture_module.__package__ = "scripts"
    sys.modules["run_page_capture"] = run_page_capture_module
    run_page_capture_spec.loader.exec_module(run_page_capture_module)

    monkeypatch.setattr(run_page_capture_module, "FeishuAppClient", DummyFeishuClient)
    # Mock _default_config_path so we don't depend on the real home directory
    monkeypatch.setattr(run_page_capture_module, "_default_config_path", lambda: config_file)

    # run_browser_capture is imported inside main(), so mock it in sys.modules
    import types
    class DummyBrowserResult(dict):
        pass

    mock_browser_module = types.ModuleType("page_capture_browser")
    mock_browser_module.run_browser_capture = lambda page_def: DummyBrowserResult({
        "page": None,
        "events": [],
        "fetch_error": None,
        "login_required": False,
        "dom_result": type("DomResult", (), {"fields": {}, "missing_fields": []})(),
    })
    sys.modules["page_capture_browser"] = mock_browser_module

    # Simulate: python run_page_capture.py --page-id baidu_poc  (no --config)
    monkeypatch.setattr(sys, "argv", ["run_page_capture.py", "--page-id", "baidu_poc"])
    run_page_capture_module.main()

    assert captured == {"app_id": "default_app_id", "app_secret": "default_app_secret"}


def test_run_capture_pipeline_url_mode_returns_ok(monkeypatch, tmp_path: Path) -> None:
    """URL mode: page_id is a raw URL, builds minimal definition, returns ok."""
    config_path = tmp_path / "page-capture.yaml"
    config_path.write_text(
        """
        feishu:
          app_id: test_app
          app_secret: test_secret
        pages: []
        """,
        encoding="utf-8",
    )

    sent = {}

    class DummyFeishuClient:
        def __init__(self, *, app_id: str, app_secret: str):
            pass

        def send_text(self, *, chat_id: str, text: str) -> str:
            sent["chat_id"] = chat_id
            sent["text"] = text
            return "om_url_test"

    class DummyBrowserResult(dict):
        pass

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
        sys.modules[f"scripts.{mod_name}"] = module
        spec.loader.exec_module(module)

    run_page_capture_spec = importlib.util.spec_from_file_location(
        "run_page_capture", SCRIPTS_DIR / "run_page_capture.py"
    )
    run_page_capture_module = importlib.util.module_from_spec(run_page_capture_spec)
    run_page_capture_module.__package__ = "scripts"
    sys.modules["run_page_capture"] = run_page_capture_module
    run_page_capture_spec.loader.exec_module(run_page_capture_module)

    mock_browser_module = types.ModuleType("page_capture_browser")
    mock_browser_module.run_browser_capture = lambda page_def: DummyBrowserResult({
        "page": None,
        "events": [],
        "fetch_error": None,
        "login_required": False,
        "dom_result": type("DomResult", (), {"fields": {}, "missing_fields": []})(),
    })
    sys.modules["page_capture_browser"] = mock_browser_module

    result = run_page_capture_module.run_capture_pipeline(
        config_path=str(config_path),
        page_id="https://www.baidu.com",
        feishu_client=DummyFeishuClient(app_id="x", app_secret="x"),
        browser_runner=mock_browser_module.run_browser_capture,
        feishu_chat_id="oc_url_chat",
    )

    assert result["state"] == "ok"
    assert result["message_id"] == "om_url_test"
    assert sent["chat_id"] == "oc_url_chat"
    assert "https://www.baidu.com" in sent["text"]
    assert "URL" in sent["text"]


def test_run_capture_pipeline_url_mode_requires_chat_id(monkeypatch, tmp_path: Path) -> None:
    """URL mode without feishu_chat_id raises ValueError."""
    config_path = tmp_path / "page-capture.yaml"
    config_path.write_text("pages: []", encoding="utf-8")

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
        sys.modules[f"scripts.{mod_name}"] = module
        spec.loader.exec_module(module)

    run_page_capture_spec = importlib.util.spec_from_file_location(
        "run_page_capture", SCRIPTS_DIR / "run_page_capture.py"
    )
    run_page_capture_module = importlib.util.module_from_spec(run_page_capture_spec)
    run_page_capture_module.__package__ = "scripts"
    sys.modules["run_page_capture"] = run_page_capture_module
    run_page_capture_spec.loader.exec_module(run_page_capture_module)

    with pytest.raises(ValueError, match="feishu_chat_id is required"):
        run_page_capture_module.run_capture_pipeline(
            config_path=str(config_path),
            page_id="https://www.baidu.com",
            feishu_client=type("Client", (), {"send_text": lambda self, **kw: "x"})(),
            browser_runner=lambda x: {},
            feishu_chat_id=None,
        )


def test_page_definition_from_url_extracts_name_from_host(tmp_path: Path) -> None:
    """URL mode builds name from URL host."""
    models_spec = importlib.util.spec_from_file_location(
        "page_capture_models", SCRIPTS_DIR / "page_capture_models.py"
    )
    models_module = importlib.util.module_from_spec(models_spec)
    sys.modules["page_capture_models"] = models_module
    models_spec.loader.exec_module(models_module)

    defs_module = models_module

    page_def = defs_module.page_definition_from_url(
        "https://httpbin.org/get", feishu_chat_id="oc_test"
    )

    assert page_def.name == "httpbin.org"
    assert page_def.url == "https://httpbin.org/get"
    assert page_def.wait_for.load_state == "networkidle"
    assert page_def.dom_fields == []
    assert page_def.feishu_target.chat_id == "oc_test"
