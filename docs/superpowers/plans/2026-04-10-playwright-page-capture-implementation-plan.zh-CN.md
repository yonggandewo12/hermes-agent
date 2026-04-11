# Playwright 页面抓取与飞书推送 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Hermes Agent 中落地一个基于 Playwright 的页面抓取框架，先用 `baidu_poc` 跑通公共抓取、手动触发、cron 调度和飞书推送，再为后续业务页面接入登录态复用与真实业务字段提取预留扩展位。

**Architecture:** 方案以一个新的业务 skill 作为统一入口，内部通过单一 Python orchestrator 串联页面配置加载、Playwright 页面运行、网络探测、DOM 提取、状态分类和飞书文本通知。百度阶段只验证公共框架，业务阶段沿用同一数据流并追加 storage state、登录态判断和真实指标提取，避免两套实现分叉。

**Tech Stack:** Python 3.11, Playwright, Hermes skills system, Hermes cron, requests, pytest, YAML 配置

---

## File Structure

### New files
- `optional-skills/communication/playwright-page-capture/SKILL.md` — 业务 skill 入口，描述百度 PoC 与后续业务页面的使用方式
- `optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py` — 主 orchestrator，负责串联配置、浏览器、提取、分类、通知
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py` — 统一的数据模型：页面配置、网络探测结果、DOM 提取结果、分类结果
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py` — 加载 `baidu_poc` 与未来业务页面的配置
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_browser.py` — Playwright 启动、页面打开、等待稳定、storage state 扩展位
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_probe.py` — 记录关键请求/响应并输出网络探测结果
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_dom.py` — 百度字段 DOM 提取与未来业务页兜底提取
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_classify.py` — 生成 `ok` / `field_missing` / `fetch_failed` / `login_required`
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_feishu.py` — 飞书应用 token 获取与文本消息发送
- `optional-skills/communication/playwright-page-capture/examples/page-capture.example.yaml` — `baidu_poc` 配置示例
- `tests/skills/test_playwright_page_capture_config.py` — 配置加载测试
- `tests/skills/test_playwright_page_capture_probe.py` — 网络探测测试
- `tests/skills/test_playwright_page_capture_dom.py` — DOM 提取测试
- `tests/skills/test_playwright_page_capture_classify.py` — 状态分类测试
- `tests/skills/test_playwright_page_capture_feishu.py` — 飞书发送测试
- `tests/skills/test_playwright_page_capture.py` — 主流程集成测试

### Existing files to modify
- `README.md` — 补充 skill 手动触发与 cron 使用示例（如需）
- `README.zh-CN.md` — 同步中文说明（如需）

### Existing files to inspect while implementing
- `tools/cronjob_tools.py` — 了解 cron prompt 与 skill 调度方式
- `tools/skills_tool.py` — 了解 skill 目录结构与加载方式
- `AGENTS.md` — 遵循项目内测试、配置、路径与 profile 约束

---

### Task 1: 搭建 Playwright 页面抓取 skill 骨架

**Files:**
- Create: `optional-skills/communication/playwright-page-capture/SKILL.md`
- Create: `optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py`
- Test: `tests/skills/test_playwright_page_capture.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_playwright_page_capture_skill_scaffold_exists():
    root = Path("optional-skills/communication/playwright-page-capture")
    assert (root / "SKILL.md").exists()
    assert (root / "scripts" / "run_page_capture.py").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture.py::test_playwright_page_capture_skill_scaffold_exists -v`
Expected: FAIL with `AssertionError` because the skill files do not exist yet.

- [ ] **Step 3: Write minimal implementation**

`optional-skills/communication/playwright-page-capture/SKILL.md`

```markdown
---
name: playwright-page-capture
description: 使用 Playwright 抓取固定页面，提取字段并将结果发送到飞书群。
metadata:
  hermes:
    tags: [communication, playwright, browser, monitoring]
    requires_toolsets: [terminal]
---

# Playwright Page Capture

## When to Use
- 用户要先用公开页面验证页面抓取框架
- 用户要对固定页面执行 Playwright 抓取并推送飞书
- 用户要通过 Hermes cron 定时触发同一抓取流程

## Inputs
- `page_id=<configured-page-id>`
- `config=<absolute-path-to-config>`

## Procedure
1. 调用 `python optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py ...`
2. 输出统一 JSON 结果
3. 使用同一 skill 支持手动与 cron 调用
```

`optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py`

```python
from __future__ import annotations

import json


def main() -> int:
    print(json.dumps({"status": "not_implemented"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture.py::test_playwright_page_capture_skill_scaffold_exists -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/SKILL.md optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py tests/skills/test_playwright_page_capture.py
git commit -m "feat(skills): scaffold playwright page capture skill"
```

### Task 2: 定义页面配置与统一数据模型

**Files:**
- Create: `optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py`
- Create: `optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py`
- Create: `optional-skills/communication/playwright-page-capture/examples/page-capture.example.yaml`
- Test: `tests/skills/test_playwright_page_capture_config.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from optional_skills_loader import load_page_capture_config


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

    config = load_page_capture_config(config_path)
    page = config.pages[0]

    assert page.page_id == "baidu_poc"
    assert page.wait_for.load_state == "networkidle"
    assert page.dom_fields[1].attribute == "name"
    assert page.feishu_target.chat_id == "oc_test_chat"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_load_page_capture_config_reads_baidu_poc_definition -v`
Expected: FAIL with `ImportError` because the config loader does not exist yet.

- [ ] **Step 3: Write minimal implementation**

`optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py`

```python
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
```

`optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py`

```python
from __future__ import annotations

from pathlib import Path
import yaml

from .page_capture_models import (
    DomFieldRule,
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
                feishu_target=FeishuTarget(**item["feishu_target"]),
                storage_state_path=item.get("storage_state_path"),
            )
        )
    return PageCaptureConfig(pages=pages)
```

`optional-skills/communication/playwright-page-capture/examples/page-capture.example.yaml`

```yaml
pages:
  - page_id: baidu_poc
    name: Baidu PoC
    url: https://www.baidu.com
    wait_for:
      load_state: networkidle
      selector: "input[name='wd']"
    network_probe:
      url_keywords: ["baidu.com"]
    dom_fields:
      - field: page_title
        kind: title
      - field: search_input_name
        selector: "input[name='wd']"
        attribute: name
        required: true
    feishu_target:
      chat_id: oc_example_chat
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_load_page_capture_config_reads_baidu_poc_definition -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py optional-skills/communication/playwright-page-capture/examples/page-capture.example.yaml tests/skills/test_playwright_page_capture_config.py
git commit -m "feat(skills): add page capture config models"
```

### Task 3: 实现 Browser Runner 与 storage state 扩展位

**Files:**
- Create: `optional-skills/communication/playwright-page-capture/scripts/page_capture_browser.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py`
- Test: `tests/skills/test_playwright_page_capture.py`

- [ ] **Step 1: Write the failing test**

```python
from optional_skills_loader import build_browser_launch_options


def test_build_browser_launch_options_includes_storage_state_when_present():
    options = build_browser_launch_options(storage_state_path="/tmp/state.json")

    assert options["headless"] is True
    assert options["storage_state"] == "/tmp/state.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture.py::test_build_browser_launch_options_includes_storage_state_when_present -v`
Expected: FAIL with `ImportError` because the browser helper does not exist yet.

- [ ] **Step 3: Write minimal implementation**

在 `page_capture_models.py` 追加：

```python
@dataclass
class BrowserLaunchOptions:
    headless: bool
    storage_state: str | None = None
```

`optional-skills/communication/playwright-page-capture/scripts/page_capture_browser.py`

```python
from __future__ import annotations

from .page_capture_models import BrowserLaunchOptions


def build_browser_launch_options(storage_state_path: str | None) -> dict[str, object]:
    return {
        "headless": True,
        "storage_state": storage_state_path,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture.py::test_build_browser_launch_options_includes_storage_state_when_present -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py optional-skills/communication/playwright-page-capture/scripts/page_capture_browser.py tests/skills/test_playwright_page_capture.py
git commit -m "feat(skills): add page capture browser options"
```

### Task 4: 实现 Network Probe

**Files:**
- Create: `optional-skills/communication/playwright-page-capture/scripts/page_capture_probe.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py`
- Test: `tests/skills/test_playwright_page_capture_probe.py`

- [ ] **Step 1: Write the failing test**

```python
from optional_skills_loader import probe_network_events


def test_probe_network_events_hits_keyword_and_status():
    events = [
        {"url": "https://www.baidu.com/api/test", "status": 200},
        {"url": "https://other.example.com/x", "status": 204},
    ]

    result = probe_network_events(events, ["baidu.com"])

    assert result.hit is True
    assert result.status == 200
    assert result.url == "https://www.baidu.com/api/test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_probe.py::test_probe_network_events_hits_keyword_and_status -v`
Expected: FAIL with `ImportError` because the probe helper does not exist yet.

- [ ] **Step 3: Write minimal implementation**

在 `page_capture_models.py` 追加：

```python
@dataclass
class NetworkProbeResult:
    hit: bool
    url: str | None
    status: int | None
```

`optional-skills/communication/playwright-page-capture/scripts/page_capture_probe.py`

```python
from __future__ import annotations

from .page_capture_models import NetworkProbeResult


def probe_network_events(events: list[dict[str, object]], url_keywords: list[str]) -> NetworkProbeResult:
    for event in events:
        url = str(event.get("url") or "")
        if any(keyword in url for keyword in url_keywords):
            return NetworkProbeResult(
                hit=True,
                url=url,
                status=int(event.get("status")) if event.get("status") is not None else None,
            )
    return NetworkProbeResult(hit=False, url=None, status=None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture_probe.py::test_probe_network_events_hits_keyword_and_status -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py optional-skills/communication/playwright-page-capture/scripts/page_capture_probe.py tests/skills/test_playwright_page_capture_probe.py
git commit -m "feat(skills): add page capture network probe"
```

### Task 5: 实现百度 DOM 字段提取

**Files:**
- Create: `optional-skills/communication/playwright-page-capture/scripts/page_capture_dom.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py`
- Test: `tests/skills/test_playwright_page_capture_dom.py`

- [ ] **Step 1: Write the failing test**

```python
from optional_skills_loader import extract_dom_fields


class DummyNode:
    def __init__(self, attrs=None):
        self.attrs = attrs or {}

    def get_attribute(self, name):
        return self.attrs.get(name)


class DummyPage:
    def __init__(self):
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

    result = extract_dom_fields(page, rules)

    assert result.fields["page_title"] == "百度一下，你就知道"
    assert result.fields["search_input_name"] == "wd"
    assert result.missing_fields == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_dom.py::test_extract_dom_fields_reads_title_and_attribute -v`
Expected: FAIL with `ImportError` because the DOM extractor does not exist yet.

- [ ] **Step 3: Write minimal implementation**

在 `page_capture_models.py` 追加：

```python
@dataclass
class DomExtractionResult:
    fields: dict[str, str]
    missing_fields: list[str]
```

`optional-skills/communication/playwright-page-capture/scripts/page_capture_dom.py`

```python
from __future__ import annotations

from .page_capture_models import DomExtractionResult, DomFieldRule


def extract_dom_fields(page, rules: list[DomFieldRule]) -> DomExtractionResult:
    fields: dict[str, str] = {}
    missing_fields: list[str] = []

    for rule in rules:
        value = None
        if rule.kind == "title":
            value = page.title()
        elif rule.selector and rule.attribute:
            node = page.query_selector(rule.selector)
            value = node.get_attribute(rule.attribute) if node else None

        if value:
            fields[rule.field] = value
        elif rule.required:
            missing_fields.append(rule.field)

    return DomExtractionResult(fields=fields, missing_fields=missing_fields)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture_dom.py::test_extract_dom_fields_reads_title_and_attribute -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py optional-skills/communication/playwright-page-capture/scripts/page_capture_dom.py tests/skills/test_playwright_page_capture_dom.py
git commit -m "feat(skills): add page capture dom extraction"
```

### Task 6: 实现状态分类器

**Files:**
- Create: `optional-skills/communication/playwright-page-capture/scripts/page_capture_classify.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py`
- Test: `tests/skills/test_playwright_page_capture_classify.py`

- [ ] **Step 1: Write the failing test**

```python
from optional_skills_loader import classify_capture_result


def test_classify_capture_result_returns_ok_when_dom_and_probe_succeed():
    state = classify_capture_result(
        fetch_error=None,
        missing_fields=[],
        probe_hit=True,
        login_required=False,
    )

    assert state == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_classify.py::test_classify_capture_result_returns_ok_when_dom_and_probe_succeed -v`
Expected: FAIL with `ImportError` because the classifier does not exist yet.

- [ ] **Step 3: Write minimal implementation**

在 `page_capture_models.py` 追加：

```python
CaptureState = str
```

`optional-skills/communication/playwright-page-capture/scripts/page_capture_classify.py`

```python
from __future__ import annotations


def classify_capture_result(*, fetch_error: str | None, missing_fields: list[str], probe_hit: bool, login_required: bool) -> str:
    if login_required:
        return "login_required"
    if fetch_error:
        return "fetch_failed"
    if missing_fields or not probe_hit:
        return "field_missing"
    return "ok"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture_classify.py -v`
Expected: PASS with cases for `ok`, `field_missing`, `fetch_failed`, and `login_required`.

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py optional-skills/communication/playwright-page-capture/scripts/page_capture_classify.py tests/skills/test_playwright_page_capture_classify.py
git commit -m "feat(skills): add page capture classifier"
```

### Task 7: 实现飞书文本通知

**Files:**
- Create: `optional-skills/communication/playwright-page-capture/scripts/page_capture_feishu.py`
- Test: `tests/skills/test_playwright_page_capture_feishu.py`

- [ ] **Step 1: Write the failing test**

```python
from optional_skills_loader import FeishuAppClient


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_feishu.py::test_feishu_client_sends_page_capture_message -v`
Expected: FAIL with `ImportError` because the client does not exist yet.

- [ ] **Step 3: Write minimal implementation**

`optional-skills/communication/playwright-page-capture/scripts/page_capture_feishu.py`

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture_feishu.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/scripts/page_capture_feishu.py tests/skills/test_playwright_page_capture_feishu.py
git commit -m "feat(skills): add feishu sender for page capture"
```

### Task 8: 串联百度 PoC 主流程

**Files:**
- Modify: `optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_browser.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_probe.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_dom.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_classify.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_feishu.py`
- Test: `tests/skills/test_playwright_page_capture.py`

- [ ] **Step 1: Write the failing test**

```python
from optional_skills_loader import run_capture_pipeline


def test_run_capture_pipeline_returns_ok_for_baidu_poc(monkeypatch, tmp_path):
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

    monkeypatch.setattr("page_capture_runner.run_browser_capture", lambda definition: {
        "page": type("DummyPage", (), {
            "title": lambda self: "百度一下，你就知道",
            "query_selector": lambda self, selector: type("Node", (), {"get_attribute": lambda self, name: "wd"})(),
        })(),
        "events": [{"url": "https://www.baidu.com/api/test", "status": 200}],
        "fetch_error": None,
        "login_required": False,
    })

    sent = {}

    class DummyFeishuClient:
        def send_text(self, *, chat_id: str, text: str) -> str:
            sent["chat_id"] = chat_id
            sent["text"] = text
            return "om_test"

    result = run_capture_pipeline(config_path=config_path, page_id="baidu_poc", feishu_client=DummyFeishuClient())

    assert result["state"] == "ok"
    assert result["message_id"] == "om_test"
    assert sent["chat_id"] == "oc_test_chat"
    assert "页面巡检结果" in sent["text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture.py::test_run_capture_pipeline_returns_ok_for_baidu_poc -v`
Expected: FAIL because `run_capture_pipeline` does not yet exist.

- [ ] **Step 3: Write minimal implementation**

将 `run_page_capture.py` 改为：

```python
from __future__ import annotations

import argparse
import json
import os

from .page_capture_classify import classify_capture_result
from .page_capture_config import load_page_capture_config
from .page_capture_dom import extract_dom_fields
from .page_capture_feishu import FeishuAppClient
from .page_capture_probe import probe_network_events


def _build_message(page_name: str, state: str, fields: dict[str, str], probe) -> str:
    if state == "ok":
        return (
            f"【页面巡检结果】\n页面：{page_name}\n状态：ok\n"
            f"页面标题：{fields.get('page_title', '')}\n"
            f"搜索框名称：{fields.get('search_input_name', '')}\n"
            f"网络探测：{'命中' if probe.hit else '未命中'}\n"
            f"网络状态码：{probe.status if probe.status is not None else ''}\n"
            "结论：公共抓取链路运行正常"
        )
    if state == "field_missing":
        return f"【页面字段缺失】\n页面：{page_name}\n状态：field_missing\n缺失字段：{','.join(sorted(set(fields.get('_missing_fields', []))))}"
    if state == "login_required":
        return f"【页面需要登录】\n页面：{page_name}\n状态：login_required\n动作：请手工登录后重试"
    return f"【页面抓取失败】\n页面：{page_name}\n状态：fetch_failed\n原因：页面加载失败、超时或提取流程异常"


def run_capture_pipeline(*, config_path: str, page_id: str, feishu_client, browser_runner):
    config = load_page_capture_config(config_path)
    page_def = next(page for page in config.pages if page.page_id == page_id)
    runtime = browser_runner(page_def)
    probe = probe_network_events(runtime["events"], page_def.network_probe.url_keywords)
    dom_result = extract_dom_fields(runtime["page"], page_def.dom_fields)
    state = classify_capture_result(
        fetch_error=runtime["fetch_error"],
        missing_fields=dom_result.missing_fields,
        probe_hit=probe.hit,
        login_required=runtime["login_required"],
    )
    fields = dict(dom_result.fields)
    fields["_missing_fields"] = dom_result.missing_fields
    text = _build_message(page_def.page_id, state, fields, probe)
    message_id = feishu_client.send_text(chat_id=page_def.feishu_target.chat_id, text=text)
    return {"state": state, "message_id": message_id}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--page-id", required=True)
    args = parser.parse_args()

    client = FeishuAppClient(
        app_id=os.environ["FEISHU_APP_ID"],
        app_secret=os.environ["FEISHU_APP_SECRET"],
    )
    raise NotImplementedError("Wire browser runner in implementation task")
```

并在同文件中补一个最小 `browser_runner` 占位：

```python
def run_browser_capture(page_def):
    raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture.py::test_run_capture_pipeline_returns_ok_for_baidu_poc -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py optional-skills/communication/playwright-page-capture/scripts/page_capture_browser.py optional-skills/communication/playwright-page-capture/scripts/page_capture_probe.py optional-skills/communication/playwright-page-capture/scripts/page_capture_dom.py optional-skills/communication/playwright-page-capture/scripts/page_capture_classify.py optional-skills/communication/playwright-page-capture/scripts/page_capture_feishu.py tests/skills/test_playwright_page_capture.py
git commit -m "feat(skills): wire baidu poc page capture pipeline"
```

### Task 9: 接入真实 Playwright 运行与等待条件

**Files:**
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_browser.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py`
- Test: `tests/skills/test_playwright_page_capture.py`

- [ ] **Step 1: Write the failing test**

```python
from optional_skills_loader import normalize_runtime_result


def test_normalize_runtime_result_returns_fetch_failed_on_navigation_error():
    result = normalize_runtime_result(page=None, events=[], fetch_error="timeout", login_required=False)

    assert result["fetch_error"] == "timeout"
    assert result["login_required"] is False
    assert result["events"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture.py::test_normalize_runtime_result_returns_fetch_failed_on_navigation_error -v`
Expected: FAIL because the runtime normalization helper does not exist.

- [ ] **Step 3: Write minimal implementation**

在 `page_capture_browser.py` 中补充：

```python
from __future__ import annotations


def normalize_runtime_result(*, page, events, fetch_error: str | None, login_required: bool) -> dict[str, object]:
    return {
        "page": page,
        "events": events,
        "fetch_error": fetch_error,
        "login_required": login_required,
    }
```

并把 Playwright 真正运行骨架实现为：

```python
from playwright.sync_api import sync_playwright


def run_browser_capture(page_def):
    events: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context_kwargs = {}
        if page_def.storage_state_path:
            context_kwargs["storage_state"] = page_def.storage_state_path
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.on("response", lambda response: events.append({"url": response.url, "status": response.status}))
        try:
            page.goto(page_def.url, wait_until=page_def.wait_for.load_state)
            if page_def.wait_for.selector:
                page.wait_for_selector(page_def.wait_for.selector)
            return normalize_runtime_result(page=page, events=events, fetch_error=None, login_required=False)
        except Exception as exc:
            return normalize_runtime_result(page=None, events=events, fetch_error=str(exc), login_required=False)
        finally:
            context.close()
            browser.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture.py::test_normalize_runtime_result_returns_fetch_failed_on_navigation_error -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/scripts/page_capture_browser.py optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py tests/skills/test_playwright_page_capture.py
git commit -m "feat(skills): add playwright browser runtime"
```

### Task 10: 文档化手动触发与 cron 调用

**Files:**
- Modify: `optional-skills/communication/playwright-page-capture/SKILL.md`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Test: none

- [ ] **Step 1: Write exact manual trigger examples**

在 `SKILL.md` 中补充：

```markdown
## Manual Trigger
- 对话触发：`使用 playwright-page-capture 处理 page_id=baidu_poc config=/abs/path/page-capture.yaml`
- CLI 触发：`hermes -q "使用 playwright-page-capture 处理 page_id=baidu_poc config=/abs/path/page-capture.yaml"`

## Cron Trigger
- 通过 `/cron add` 创建定时任务，prompt 中调用同一个 skill：
  `使用 playwright-page-capture 处理 page_id=baidu_poc config=/abs/path/page-capture.yaml`
```

- [ ] **Step 2: Update README.md with a minimal example**

```markdown
### Playwright Page Capture Skill Example

A page capture workflow can:
- open a fixed page with Playwright
- probe network responses
- extract DOM fields
- send results to a Feishu group

Manual run example:

```bash
hermes -q "Use playwright-page-capture for page_id=baidu_poc config=/abs/path/page-capture.yaml"
```
```

- [ ] **Step 3: Update README.zh-CN.md with a matching Chinese example**

```markdown
### Playwright 页面抓取 Skill 示例

可以用业务 skill 实现如下流程：
- 用 Playwright 打开固定页面
- 监听网络响应并提取页面字段
- 将结果发送到飞书群

手动执行示例：

```bash
hermes -q "使用 playwright-page-capture 处理 page_id=baidu_poc config=/abs/path/page-capture.yaml"
```
```

- [ ] **Step 4: Verify the docs mention the new skill**

Run: `python - <<'PY'
from pathlib import Path
for path in [Path('optional-skills/communication/playwright-page-capture/SKILL.md'), Path('README.md'), Path('README.zh-CN.md')]:
    text = path.read_text(encoding='utf-8')
    assert 'playwright-page-capture' in text
print('ok')
PY`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture/SKILL.md README.md README.zh-CN.md
git commit -m "docs: document playwright page capture skill"
```

### Task 11: 完整验证百度 PoC 闭环

**Files:**
- Modify: `optional-skills/communication/playwright-page-capture/scripts/*.py`
- Modify: `tests/skills/test_playwright_page_capture*.py`
- Test: `tests/skills/test_playwright_page_capture.py`
- Test: `tests/skills/test_playwright_page_capture_config.py`
- Test: `tests/skills/test_playwright_page_capture_probe.py`
- Test: `tests/skills/test_playwright_page_capture_dom.py`
- Test: `tests/skills/test_playwright_page_capture_classify.py`
- Test: `tests/skills/test_playwright_page_capture_feishu.py`

- [ ] **Step 1: Run the focused test suite**

Run: `pytest tests/skills/test_playwright_page_capture.py tests/skills/test_playwright_page_capture_config.py tests/skills/test_playwright_page_capture_probe.py tests/skills/test_playwright_page_capture_dom.py tests/skills/test_playwright_page_capture_classify.py tests/skills/test_playwright_page_capture_feishu.py -v`
Expected: PASS; if failures appear, use their messages to drive the next edits.

- [ ] **Step 2: Fix import paths and type consistency issues**

重点统一以下导入：

```python
from .page_capture_config import load_page_capture_config
from .page_capture_browser import run_browser_capture
from .page_capture_probe import probe_network_events
from .page_capture_dom import extract_dom_fields
from .page_capture_classify import classify_capture_result
from .page_capture_feishu import FeishuAppClient
```

以及以下模型名：

```python
PageCaptureDefinition
NetworkProbeResult
DomExtractionResult
CaptureState
```

- [ ] **Step 3: Re-run the focused test suite**

Run: `pytest tests/skills/test_playwright_page_capture.py tests/skills/test_playwright_page_capture_config.py tests/skills/test_playwright_page_capture_probe.py tests/skills/test_playwright_page_capture_dom.py tests/skills/test_playwright_page_capture_classify.py tests/skills/test_playwright_page_capture_feishu.py -v`
Expected: PASS

- [ ] **Step 4: Run a CLI smoke check**

Run: `python optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py --help`
Expected: exit code 0 and usage output including `--config` and `--page-id`.

- [ ] **Step 5: Commit**

```bash
git add optional-skills/communication/playwright-page-capture tests/skills README.md README.zh-CN.md
git commit -m "feat(skills): add playwright page capture workflow"
```

---

## Self-Review

### Spec coverage
- 百度 `baidu_poc` 框架验证：Task 2, Task 8, Task 11
- Playwright 页面运行：Task 3, Task 9
- Network Probe：Task 4, Task 8
- DOM 提取：Task 5, Task 8
- 状态模型 `ok` / `field_missing` / `fetch_failed` / `login_required`：Task 6, Task 8
- 飞书通知：Task 7, Task 8
- 手动触发与 cron 说明：Task 10
- 业务阶段 storage state 扩展位：Task 2, Task 3, Task 9

### Placeholder scan
- 无 `TODO` / `TBD` / “similar to” 占位描述
- 每个任务都给出明确文件路径、命令与代码片段
- 每个测试步骤都有具体命令与预期

### Type consistency
- `PageCaptureDefinition` 贯穿配置、浏览器与主流程
- `probe_network_events`, `extract_dom_fields`, `classify_capture_result`, `run_capture_pipeline` 在各任务中保持同名
- `login_required` 作为扩展状态在分类器中先定义，业务阶段可直接启用
