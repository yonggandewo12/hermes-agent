import sys
import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "optional-skills" / "communication" / "playwright-page-capture" / "scripts"

spec = importlib.util.spec_from_file_location("page_capture_dom", f"{SCRIPTS_DIR}/page_capture_dom.py")
page_capture_dom = importlib.util.module_from_spec(spec)
sys.modules["page_capture_dom"] = page_capture_dom

spec_models = importlib.util.spec_from_file_location("page_capture_models", f"{SCRIPTS_DIR}/page_capture_models.py")
page_capture_models = importlib.util.module_from_spec(spec_models)
sys.modules["page_capture_models"] = page_capture_models

spec_models.loader.exec_module(page_capture_models)
spec.loader.exec_module(page_capture_dom)

DomFieldRule = page_capture_models.DomFieldRule
extract_dom_fields = page_capture_dom.extract_dom_fields


class DummyNode:
    def __init__(self, attrs: dict | None = None) -> None:
        self.attrs = attrs or {}
    def get_attribute(self, name: str) -> str | None:
        return self.attrs.get(name)

class DummyPage:
    def __init__(self) -> None:
        self.title_text = "百度一下，你就知道"
        self.nodes = {"input[name='wd']": DummyNode({"name": "wd"})}
    def title(self):
        return self.title_text
    def query_selector(self, selector):
        return self.nodes.get(selector)


def test_extract_dom_fields_reads_title_and_attribute():
    page = DummyPage()
    rules = [
        {"field": "page_title", "kind": "title"},
        {"field": "search_input_name", "selector": "input[name='wd']", "attribute": "name", "required": True},
    ]
    rules = [DomFieldRule(**r) for r in rules]
    result = extract_dom_fields(page, rules)
    assert result.fields["page_title"] == "百度一下，你就知道"
    assert result.fields["search_input_name"] == "wd"
    assert result.missing_fields == []


if __name__ == "__main__":
    test_extract_dom_fields_reads_title_and_attribute()
    print("All tests passed!")
