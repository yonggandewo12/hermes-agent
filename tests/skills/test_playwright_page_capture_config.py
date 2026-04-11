import pytest
import sys
from pathlib import Path
import importlib.util

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