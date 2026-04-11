from __future__ import annotations
import requests


class FeishuAppClient:
    def __init__(self, *, app_id: str, app_secret: str, base_url: str = "https://open.feishu.cn/open-apis"):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url.rstrip("/")

    def _get_tenant_access_token(self) -> str:
        response = requests.post(
            f"{self.base_url}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["tenant_access_token"]

    def send_text(self, *, chat_id: str, text: str) -> str:
        token = self._get_tenant_access_token()
        response = requests.post(
            f"{self.base_url}/im/v1/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": chat_id,
                "msg_type": "text",
                "content": '{"text": "%s"}' % text.replace('"', '\\"'),
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["data"]["message_id"]
