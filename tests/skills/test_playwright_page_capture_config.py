import pytest
import sys
from pathlib import Path
import importlib.util
import yaml

from hermes_cli import tools_config

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "optional-skills"
    / "communication"
    / "playwright-page-capture"
    / "scripts"
    / "page_capture_config.py"
)

SCRIPTS_DIR = SCRIPT_PATH.parent

def load_module():
    # Add scripts directory to sys.path so modules can be found
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("page_capture_config", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_load_page_capture_config_reads_baidu_poc_definition(tmp_path: Path):
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
    module = load_module()
    config = module.load_page_capture_config(config_path)
    page = config.pages[0]
    assert page.page_id == "baidu_poc"
    assert page.wait_for.load_state == "networkidle"
    assert page.dom_fields[1].attribute == "name"
    assert page.feishu_target.chat_id == "oc_test_chat"
def test_load_page_capture_config_rejects_partial_feishu(tmp_path: Path):
    """Partial feishu config (missing app_secret) raises ValueError."""
    config_path = tmp_path / "page-capture.yaml"
    config_path.write_text(
        """
        feishu:
          app_id: cli_from_config
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
    module = load_module()
    with pytest.raises(ValueError, match="app_id and app_secret"):
        module.load_page_capture_config(config_path)

def test_write_playwright_page_capture_config_creates_feishu_section(tmp_path: Path, monkeypatch):
    target = tmp_path / "playwright-page-capture.yaml"
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    tools_config._write_playwright_page_capture_config(
        app_id="cli_test",
        app_secret="secret_test",
    )

    content = target.read_text(encoding="utf-8")
    assert "feishu:" in content
    assert "app_id: cli_test" in content
    assert "app_secret: secret_test" in content

def test_write_playwright_page_capture_config_preserves_other_content(tmp_path: Path, monkeypatch):
    target = tmp_path / "playwright-page-capture.yaml"
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    target.write_text(
        yaml.dump(
            {
                "pages": [
                    {
                        "page_id": "existing",
                        "url": "https://example.com",
                    }
                ]
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    tools_config._write_playwright_page_capture_config(
        app_id="cli_updated",
        app_secret="secret_updated",
    )

    config = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert "pages" in config
    assert config["pages"][0]["page_id"] == "existing"
    assert config["feishu"]["app_id"] == "cli_updated"
    assert config["feishu"]["app_secret"] == "secret_updated"


def test_append_playwright_page_capture_page_adds_minimal_page(tmp_path: Path, monkeypatch):
    target = tmp_path / "playwright-page-capture.yaml"
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    tools_config._write_playwright_page_capture_config(app_id="cli_test", app_secret="secret_test")

    tools_config._append_playwright_page_capture_page(
        page_id="baidu_poc",
        name="百度搜索 PoC",
        url="https://www.baidu.com",
        chat_id="oc_xxx",
    )

    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    page = loaded["pages"][0]
    assert page["page_id"] == "baidu_poc"
    assert page["wait_for"]["load_state"] == "networkidle"
    assert page["feishu_target"]["chat_id"] == "oc_xxx"


def test_setup_playwright_page_capture_prompts_for_example_page(monkeypatch, tmp_path):
    target = tmp_path / "playwright-page-capture.yaml"
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    answers = [
        "y",              # configure skill
        "cli_test",       # app id
        "secret_test",    # app secret
        "y",              # create example page
        "baidu_poc",      # page id
        "百度搜索 PoC",     # name
        "https://www.baidu.com",  # url
        "oc_xxx",         # chat id
    ]
    answers_iter = iter(answers)
    def mock_prompt(question, default=None, password=False):
        return next(answers_iter)
    monkeypatch.setattr(tools_config, "_prompt", mock_prompt)

    path = tools_config._setup_playwright_page_capture()

    assert path == target
    assert target.exists()
    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert loaded["feishu"]["app_id"] == "cli_test"
    assert loaded["pages"][0]["name"] == "百度搜索 PoC"


def test_setup_playwright_page_capture_updates_feishu_without_removing_existing_pages(monkeypatch, tmp_path):
    target = tmp_path / "playwright-page-capture.yaml"
    target.write_text(
        yaml.dump(
            {
                "feishu": {"app_id": "old", "app_secret": "old_secret"},
                "pages": [{"page_id": "existing", "name": "Existing", "url": "https://example.com", "feishu_target": {"chat_id": "oc_old"}}],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    answers = [
        "y",           # configure skill
        "cli_new",     # app id
        "secret_new",  # app secret
        "n",           # skip example page
    ]
    answers_iter = iter(answers)
    def mock_prompt(question, default=None, password=False):
        return next(answers_iter)
    monkeypatch.setattr(tools_config, "_prompt", mock_prompt)

    tools_config._setup_playwright_page_capture()

    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert loaded["feishu"]["app_id"] == "cli_new"
    assert loaded["pages"][0]["page_id"] == "existing"
