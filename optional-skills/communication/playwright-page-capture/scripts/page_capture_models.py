from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def resolve_storage_state_path(storage_state_path: str | None) -> str | None:
    """
    Resolve storage_state_path to an absolute path string for Playwright.

    Rules:
      - None → None (no auth state)
      - Absolute path (starts with /) → use as-is
      - Relative path → resolve against ~/.hermes/stats/ (create dir if needed)
    """
    if not storage_state_path:
        return None
    p = Path(storage_state_path).expanduser()
    if p.is_absolute():
        return str(p)
    # Resolve relative to ~/.hermes/stats/
    resolved = Path.home() / ".hermes" / "stats" / p
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return str(resolved)


@dataclass
class WaitForConfig:
    load_state: str = "networkidle"
    selector: str | None = None


@dataclass
class NetworkProbeConfig:
    url_keywords: list[str] = field(default_factory=list)


@dataclass
class DomFieldRule:
    field: str
    kind: str | None = None
    selector: str | None = None
    attribute: str | None = None
    required: bool = True


@dataclass
class FeishuTarget:
    chat_id: str


@dataclass
class FeishuAppConfig:
    app_id: str
    app_secret: str
    base_url: str = "https://open.feishu.cn/open-apis"


@dataclass
class PageCaptureDefinition:
    page_id: str
    name: str
    url: str
    wait_for: WaitForConfig
    network_probe: NetworkProbeConfig
    dom_fields: list[DomFieldRule]
    feishu_target: FeishuTarget
    storage_state_path: str | None = None


@dataclass
class PageCaptureConfig:
    pages: list[PageCaptureDefinition]
    feishu: FeishuAppConfig | None = None


@dataclass
class NetworkProbeResult:
    hit: bool
    url: str | None
    status: int | None


@dataclass
class DomExtractionResult:
    fields: dict[str, str]
    missing_fields: list[str]


CaptureState = str


def page_definition_from_url(url: str, *, feishu_chat_id: str) -> PageCaptureDefinition:
    """Build a minimal PageCaptureDefinition for a raw URL (URL mode)."""
    # Extract name from URL host
    from urllib.parse import urlparse
    parsed = urlparse(url)
    name = parsed.netloc or url

    return PageCaptureDefinition(
        page_id=url,
        name=name,
        url=url,
        wait_for=WaitForConfig(load_state="networkidle"),
        network_probe=NetworkProbeConfig(url_keywords=[]),
        dom_fields=[],
        feishu_target=FeishuTarget(chat_id=feishu_chat_id),
        storage_state_path=None,
    )