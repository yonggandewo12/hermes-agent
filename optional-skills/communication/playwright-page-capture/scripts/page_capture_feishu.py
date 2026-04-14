from __future__ import annotations

import json
import requests


class FeishuAppClient:
    def __init__(self, *, app_id: str, app_secret: str, base_url: str = "https://open.feishu.cn/open-apis"):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url.rstrip("/") if base_url else "https://open.feishu.cn/open-apis"

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
            f"{self.base_url}/im/v1/messages?receive_id_type=chat_id",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["data"]["message_id"]

    def list_chats(self) -> list[dict]:
        """
        获取机器人所在的所有群聊列表。
        返回 list[dict]，每项含 chat_id, name, member_count 等字段。
        """
        token = self._get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        chats = []
        page_token = None

        while True:
            params = {"page_size": 50}
            if page_token:
                params["page_token"] = page_token
            response = requests.get(
                f"{self.base_url}/im/v1/chats",
                headers=headers,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            chats.extend(data.get("data", {}).get("items", []))
            page_token = data.get("data", {}).get("page_token")
            if not page_token:
                break

        return chats
