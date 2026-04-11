from __future__ import annotations
from dataclasses import dataclass, field


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