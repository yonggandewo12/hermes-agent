from __future__ import annotations

from pathlib import Path

import yaml

try:
    from .page_capture_models import (
        DomFieldRule,
        FeishuAppConfig,
        FeishuTarget,
        NetworkProbeConfig,
        PageCaptureConfig,
        PageCaptureDefinition,
        WaitForConfig,
    )
except ImportError:
    from page_capture_models import (
        DomFieldRule,
        FeishuAppConfig,
        FeishuTarget,
        NetworkProbeConfig,
        PageCaptureConfig,
        PageCaptureDefinition,
        WaitForConfig,
    )


def load_page_capture_config(path: str | Path) -> PageCaptureConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    pages = []
    for item in raw.get("pages", []):
        pages.append(
            PageCaptureDefinition(
                page_id=item["page_id"],
                name=item["name"],
                url=item["url"],
                wait_for=WaitForConfig(**item.get("wait_for", {})),
                network_probe=NetworkProbeConfig(**item.get("network_probe", {})),
                dom_fields=[DomFieldRule(**rule) for rule in item.get("dom_fields", [])],
                feishu_target=FeishuTarget(**item["feishu_target"]) if "feishu_target" in item else None,
                storage_state_path=item.get("storage_state_path"),
            )
        )
    feishu = raw.get("feishu")
    if feishu:
        if "app_id" in feishu and "app_secret" in feishu:
            feishu_config = FeishuAppConfig(**feishu)
        else:
            raise ValueError("feishu config requires both app_id and app_secret")
    else:
        feishu_config = None
    return PageCaptureConfig(
        pages=pages,
        feishu=feishu_config,
    )