import sys
from pathlib import Path

SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "optional-skills"
    / "communication"
    / "playwright-page-capture"
    / "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

import importlib.util

spec = importlib.util.spec_from_file_location(
    "page_capture_feishu", SCRIPTS_DIR / "page_capture_feishu.py"
)
feishu_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feishu_module)
FeishuAppClient = feishu_module.FeishuAppClient

import requests


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def test_feishu_client_sends_page_capture_message(monkeypatch):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=15):
        calls.append((url, json, headers))
        if url.endswith("/tenant_access_token/internal"):
            return DummyResponse({"tenant_access_token": "tenant-token"})
        return DummyResponse({"data": {"message_id": "om_test"}})

    monkeypatch.setattr("requests.post", fake_post)
    client = FeishuAppClient(app_id="cli_a", app_secret="secret")
    message_id = client.send_text(chat_id="oc_test_chat", text="hello")
    assert message_id == "om_test"
    assert calls[0][0].endswith("/tenant_access_token/internal")
    assert calls[1][0].endswith("/im/v1/messages")
