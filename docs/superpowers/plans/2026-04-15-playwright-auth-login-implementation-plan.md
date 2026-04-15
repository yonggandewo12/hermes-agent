# Playwright Auth Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `playwright-auth-login` skill that performs site-configured username/password login, saves Playwright storage state, and can optionally run linked `playwright-page-capture` jobs afterward.

**Architecture:** Add a sibling optional skill under `optional-skills/communication/playwright-auth-login/` with its own config/model/runner/CLI modules and tests. Extend the existing page-capture config model to record `auth_site_id`, then let the auth CLI reuse the existing `run_capture_pipeline()` entrypoint to execute linked pages without reimplementing capture or Feishu logic.

**Tech Stack:** Python, PyYAML, Playwright sync API, pytest, Hermes optional skills

---

## File Structure

### New files
- `optional-skills/communication/playwright-auth-login/DESCRIPTION.md` — skill catalog entry mirroring the page-capture skill style
- `optional-skills/communication/playwright-auth-login/SKILL.md` — user-facing usage guide, config format, examples, and result JSON
- `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_models.py` — auth dataclasses and storage-state helpers reused by config/runner/CLI
- `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_config.py` — YAML loader for `~/.hermes/playwright-auth.yaml`
- `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_runner.py` — Playwright login step execution, success checks, and orchestration helpers
- `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_login.py` — CLI entrypoint for `/playwright-auth-login`
- `tests/skills/test_playwright_auth_login.py` — skill scaffold and CLI/orchestration tests
- `tests/skills/test_playwright_auth_config.py` — config parsing tests
- `tests/skills/test_playwright_auth_runner.py` — runner step execution and status tests

### Modified files
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py` — add `auth_site_id` to `PageCaptureDefinition`
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py` — parse `auth_site_id` from YAML
- `optional-skills/communication/playwright-page-capture/SKILL.md` — document the new `auth_site_id` linkage and auth-login handoff
- `tests/skills/test_playwright_page_capture_config.py` — cover parsing of `auth_site_id`

---

### Task 1: Extend page-capture config to store auth linkage

**Files:**
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py`
- Modify: `tests/skills/test_playwright_page_capture_config.py`

- [ ] **Step 1: Write the failing config test for `auth_site_id` parsing**

```python
def test_load_page_capture_config_reads_auth_site_id(tmp_path: Path):
    config_path = tmp_path / "page-capture.yaml"
    config_path.write_text(
        """
        pages:
          - page_id: dashboard_main
            name: Dashboard Main
            url: https://example.com/dashboard
            auth_site_id: feishu_admin
            wait_for:
              load_state: networkidle
            network_probe:
              url_keywords: [example.com]
            dom_fields: []
            feishu_target:
              chat_id: oc_test_chat
        """,
        encoding="utf-8",
    )

    module = load_module()
    config = module.load_page_capture_config(config_path)

    assert config.pages[0].auth_site_id == "feishu_admin"
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_load_page_capture_config_reads_auth_site_id -v`
Expected: FAIL with `AttributeError` or constructor error because `auth_site_id` is not defined on `PageCaptureDefinition`.

- [ ] **Step 3: Add `auth_site_id` to the page-capture model**

```python
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
    auth_site_id: str | None = None
```

- [ ] **Step 4: Parse `auth_site_id` from YAML config**

```python
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
        auth_site_id=item.get("auth_site_id"),
    )
)
```

- [ ] **Step 5: Run the targeted config tests to verify they pass**

Run: `pytest tests/skills/test_playwright_page_capture_config.py -v`
Expected: PASS, including the new `auth_site_id` assertion and existing config coverage.

- [ ] **Step 6: Commit the config linkage change**

```bash
git add tests/skills/test_playwright_page_capture_config.py \
  optional-skills/communication/playwright-page-capture/scripts/page_capture_models.py \
  optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py
git commit -m "feat: add auth linkage to page capture config"
```

### Task 2: Add auth config models and loader

**Files:**
- Create: `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_models.py`
- Create: `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_config.py`
- Create: `tests/skills/test_playwright_auth_config.py`

- [ ] **Step 1: Write the failing auth config tests**

```python
def test_load_playwright_auth_config_reads_site_definition(tmp_path: Path):
    config_path = tmp_path / "playwright-auth.yaml"
    config_path.write_text(
        """
        sites:
          - site_id: feishu_admin
            name: Feishu Admin
            login_url: https://example.com/login
            username: demo_user
            password: demo_pass
            storage_state_path: feishu/feishu_admin.js
            steps:
              - action: fill
                selector: "input[name='username']"
                value_from: username
            success_criteria:
              url_not_contains: ["/login"]
        """,
        encoding="utf-8",
    )

    module = load_module()
    config = module.load_playwright_auth_config(config_path)

    site = config.sites[0]
    assert site.site_id == "feishu_admin"
    assert site.steps[0].value_from == "username"
    assert site.success_criteria.url_not_contains == ["/login"]


def test_load_playwright_auth_config_rejects_missing_credentials(tmp_path: Path):
    config_path = tmp_path / "playwright-auth.yaml"
    config_path.write_text(
        """
        sites:
          - site_id: broken
            name: Broken
            login_url: https://example.com/login
            username: demo_user
            storage_state_path: broken.js
            steps: []
            success_criteria: {}
        """,
        encoding="utf-8",
    )

    module = load_module()
    with pytest.raises(KeyError, match="password"):
        module.load_playwright_auth_config(config_path)
```

- [ ] **Step 2: Run the auth config tests to verify they fail**

Run: `pytest tests/skills/test_playwright_auth_config.py -v`
Expected: FAIL because the auth config loader modules do not exist yet.

- [ ] **Step 3: Implement auth dataclasses and storage-state path resolution**

```python
from dataclasses import dataclass, field
from pathlib import Path


def resolve_auth_storage_state_path(storage_state_path: str) -> str:
    p = Path(storage_state_path).expanduser()
    if p.is_absolute():
        return str(p)
    resolved = Path.home() / ".hermes" / "stats" / p
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return str(resolved)


@dataclass
class AuthStep:
    action: str
    selector: str | None = None
    value_from: str | None = None
    url_contains: str | None = None
    url_not_contains: str | None = None


@dataclass
class AuthSuccessCriteria:
    url_contains: list[str] = field(default_factory=list)
    url_not_contains: list[str] = field(default_factory=list)
    cookie_names: list[str] = field(default_factory=list)


@dataclass
class AuthSiteDefinition:
    site_id: str
    name: str
    login_url: str
    username: str
    password: str
    storage_state_path: str
    steps: list[AuthStep]
    success_criteria: AuthSuccessCriteria


@dataclass
class PlaywrightAuthConfig:
    sites: list[AuthSiteDefinition]
```

- [ ] **Step 4: Implement the auth YAML loader**

```python
def load_playwright_auth_config(path: str | Path) -> PlaywrightAuthConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    sites = []
    for item in raw.get("sites", []):
        sites.append(
            AuthSiteDefinition(
                site_id=item["site_id"],
                name=item["name"],
                login_url=item["login_url"],
                username=item["username"],
                password=item["password"],
                storage_state_path=item["storage_state_path"],
                steps=[AuthStep(**step) for step in item.get("steps", [])],
                success_criteria=AuthSuccessCriteria(**item.get("success_criteria", {})),
            )
        )
    return PlaywrightAuthConfig(sites=sites)
```

- [ ] **Step 5: Run the auth config tests to verify they pass**

Run: `pytest tests/skills/test_playwright_auth_config.py -v`
Expected: PASS for both valid config loading and missing-password rejection.

- [ ] **Step 6: Commit the auth config foundation**

```bash
git add tests/skills/test_playwright_auth_config.py \
  optional-skills/communication/playwright-auth-login/scripts/playwright_auth_models.py \
  optional-skills/communication/playwright-auth-login/scripts/playwright_auth_config.py
git commit -m "feat: add playwright auth config loader"
```

### Task 3: Implement auth runner step execution and login status classification

**Files:**
- Create: `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_runner.py`
- Create: `tests/skills/test_playwright_auth_runner.py`

- [ ] **Step 1: Write failing runner tests for success and step failure**

```python
def test_run_auth_flow_executes_steps_and_saves_storage_state(tmp_path: Path):
    site = AuthSiteDefinition(
        site_id="feishu_admin",
        name="Feishu Admin",
        login_url="https://example.com/login",
        username="demo_user",
        password="demo_pass",
        storage_state_path="feishu/feishu_admin.js",
        steps=[
            AuthStep(action="fill", selector="input[name='username']", value_from="username"),
            AuthStep(action="fill", selector="input[name='password']", value_from="password"),
            AuthStep(action="click", selector="button[type='submit']"),
            AuthStep(action="wait_for_url", url_not_contains="/login"),
        ],
        success_criteria=AuthSuccessCriteria(url_not_contains=["/login"], cookie_names=["session"]),
    )

    page = DummyPage(url="https://example.com/home")
    context = DummyContext(cookies=[{"name": "session_id"}])
    result = module.run_auth_flow(site, playwright_factory=lambda: DummyPlaywright(page, context))

    assert result["status"] == "success"
    assert result["storage_state_path"].endswith("feishu/feishu_admin.js")
    assert page.actions == [
        ("goto", "https://example.com/login"),
        ("fill", "input[name='username']", "demo_user"),
        ("fill", "input[name='password']", "demo_pass"),
        ("click", "button[type='submit']"),
        ("wait_for_url_not_contains", "/login"),
    ]


def test_run_auth_flow_returns_step_failed_for_missing_selector():
    site = AuthSiteDefinition(
        site_id="broken",
        name="Broken",
        login_url="https://example.com/login",
        username="demo_user",
        password="demo_pass",
        storage_state_path="broken.js",
        steps=[AuthStep(action="click", selector="button.missing")],
        success_criteria=AuthSuccessCriteria(),
    )

    result = module.run_auth_flow(site, playwright_factory=lambda: FailingPlaywright("button.missing"))

    assert result["status"] == "step_failed"
    assert result["failed_step"] == 1
    assert "button.missing" in result["error"]
```

- [ ] **Step 2: Run the runner tests to verify they fail**

Run: `pytest tests/skills/test_playwright_auth_runner.py -v`
Expected: FAIL because the runner module does not exist yet.

- [ ] **Step 3: Implement step execution and success evaluation**

```python
def _step_value(site: AuthSiteDefinition, value_from: str | None) -> str:
    if value_from == "username":
        return site.username
    if value_from == "password":
        return site.password
    raise ValueError(f"Unsupported value_from: {value_from}")


def _run_step(page, site: AuthSiteDefinition, step: AuthStep) -> None:
    if step.action == "fill":
        page.fill(step.selector, _step_value(site, step.value_from))
        return
    if step.action == "click":
        page.click(step.selector)
        return
    if step.action == "wait_for_selector":
        page.wait_for_selector(step.selector)
        return
    if step.action == "wait_for_url":
        if step.url_contains:
            page.wait_for_url(lambda current: step.url_contains in current)
            return
        if step.url_not_contains:
            page.wait_for_url(lambda current: step.url_not_contains not in current)
            return
    raise ValueError(f"Unsupported auth step: {step.action}")


def _login_success(page, context, criteria: AuthSuccessCriteria) -> bool:
    current_url = page.url
    if criteria.url_contains and not all(fragment in current_url for fragment in criteria.url_contains):
        return False
    if criteria.url_not_contains and any(fragment in current_url for fragment in criteria.url_not_contains):
        return False
    if criteria.cookie_names:
        cookies = context.cookies()
        names = [cookie["name"].lower() for cookie in cookies]
        return any(expected.lower() in name for expected in criteria.cookie_names for name in names)
    return True
```

- [ ] **Step 4: Implement the runner entrypoint with structured results**

```python
def run_auth_flow(site: AuthSiteDefinition, playwright_factory=sync_playwright) -> dict[str, object]:
    resolved_storage = resolve_auth_storage_state_path(site.storage_state_path)
    with playwright_factory() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(site.login_url, wait_until="domcontentloaded", timeout=30000)
            for index, step in enumerate(site.steps, start=1):
                try:
                    _run_step(page, site, step)
                except Exception as exc:
                    return {
                        "status": "step_failed",
                        "site_id": site.site_id,
                        "failed_step": index,
                        "error": str(exc),
                    }
            if not _login_success(page, context, site.success_criteria):
                return {
                    "status": "login_failed",
                    "site_id": site.site_id,
                    "error": "success criteria not satisfied",
                }
            context.storage_state(path=resolved_storage)
            return {
                "status": "success",
                "site_id": site.site_id,
                "storage_state_path": resolved_storage,
            }
        finally:
            context.close()
            browser.close()
```

- [ ] **Step 5: Run the runner tests to verify they pass**

Run: `pytest tests/skills/test_playwright_auth_runner.py -v`
Expected: PASS for the success path and the structured `step_failed` path.

- [ ] **Step 6: Commit the auth runner implementation**

```bash
git add tests/skills/test_playwright_auth_runner.py \
  optional-skills/communication/playwright-auth-login/scripts/playwright_auth_runner.py
git commit -m "feat: add playwright auth runner"
```

### Task 4: Add linked page orchestration and auth CLI entrypoint

**Files:**
- Create: `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_login.py`
- Modify: `optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py`
- Create: `tests/skills/test_playwright_auth_login.py`

- [ ] **Step 1: Write failing CLI tests for login-only and linked-page execution**

```python
def test_run_linked_pages_uses_auth_site_id(tmp_path: Path):
    capture_config = tmp_path / "playwright-page-capture.yaml"
    capture_config.write_text(
        """
        pages:
          - page_id: dashboard_main
            name: Dashboard Main
            url: https://example.com/dashboard
            auth_site_id: feishu_admin
            wait_for:
              load_state: networkidle
            network_probe:
              url_keywords: [example.com]
            dom_fields: []
            feishu_target:
              chat_id: oc_test_chat
        """,
        encoding="utf-8",
    )

    results = module.run_linked_pages(
        capture_config_path=str(capture_config),
        site_id="feishu_admin",
        storage_state_path="feishu/feishu_admin.js",
        feishu_client=object(),
        browser_runner=lambda page_def: {},
        capture_runner=lambda **kwargs: {"state": "ok", "message_id": "om_test"},
    )

    assert results == [
        {"page_id": "dashboard_main", "status": "ok", "message_id": "om_test"}
    ]


def test_main_prints_success_with_linked_pages(monkeypatch, capsys):
    monkeypatch.setattr(module, "_default_auth_config_path", lambda: Path("/tmp/auth.yaml"))
    monkeypatch.setattr(module, "_default_capture_config_path", lambda: Path("/tmp/capture.yaml"))
    monkeypatch.setattr(module, "load_playwright_auth_config", lambda path: PlaywrightAuthConfig(sites=[SITE]))
    monkeypatch.setattr(module, "run_auth_flow", lambda site: {
        "status": "success",
        "site_id": site.site_id,
        "storage_state_path": "/tmp/feishu_admin.js",
    })
    monkeypatch.setattr(module, "run_linked_pages", lambda **kwargs: [
        {"page_id": "dashboard_main", "status": "ok", "message_id": "om_test"}
    ])

    monkeypatch.setattr(sys, "argv", ["playwright_auth_login.py", "--site-id", "feishu_admin", "--run-linked-pages"])
    assert module.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "success"
    assert payload["capture_summary"] == {"total": 1, "ok": 1, "failed": 0}
```

- [ ] **Step 2: Run the CLI tests to verify they fail**

Run: `pytest tests/skills/test_playwright_auth_login.py -v`
Expected: FAIL because the auth CLI and orchestration helpers do not exist yet.

- [ ] **Step 3: Extract reusable linked-page lookup and summary helpers into the auth CLI**

```python
def run_linked_pages(*, capture_config_path: str, site_id: str, storage_state_path: str, feishu_client, browser_runner, capture_runner=run_capture_pipeline) -> list[dict[str, object]]:
    config = load_page_capture_config(capture_config_path)
    linked_pages = [page for page in config.pages if page.auth_site_id == site_id]
    results = []
    for page in linked_pages:
        capture_result = capture_runner(
            config_path=capture_config_path,
            page_id=page.page_id,
            feishu_client=feishu_client,
            browser_runner=browser_runner,
            storage_state=storage_state_path,
        )
        results.append(
            {
                "page_id": page.page_id,
                "status": capture_result["state"],
                "message_id": capture_result.get("message_id"),
            }
        )
    return results


def summarize_linked_pages(results: list[dict[str, object]]) -> dict[str, int]:
    failed_statuses = {"fetch_failed", "login_required"}
    return {
        "total": len(results),
        "ok": sum(1 for item in results if item["status"] == "ok"),
        "failed": sum(1 for item in results if item["status"] in failed_statuses),
    }
```

- [ ] **Step 4: Implement the auth CLI entrypoint and reuse page capture dependencies**

```python
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--capture-config", default=None)
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--run-linked-pages", action="store_true")
    args = parser.parse_args()

    auth_config_path = args.config or str(_default_auth_config_path())
    capture_config_path = args.capture_config or str(_default_capture_config_path())
    auth_config = load_playwright_auth_config(auth_config_path)
    site = next(site for site in auth_config.sites if site.site_id == args.site_id)

    result = run_auth_flow(site)
    if result["status"] != "success":
        print(json.dumps(result, ensure_ascii=False))
        return 0

    linked_pages = []
    if args.run_linked_pages:
        from page_capture_browser import run_browser_capture
        feishu_client = build_feishu_client(capture_config_path)
        linked_pages = run_linked_pages(
            capture_config_path=capture_config_path,
            site_id=site.site_id,
            storage_state_path=result["storage_state_path"],
            feishu_client=feishu_client,
            browser_runner=run_browser_capture,
        )
        result["linked_pages"] = linked_pages
        result["capture_summary"] = summarize_linked_pages(linked_pages)

    print(json.dumps(result, ensure_ascii=False))
    return 0
```

- [ ] **Step 5: Run the auth CLI tests to verify they pass**

Run: `pytest tests/skills/test_playwright_auth_login.py -v`
Expected: PASS for linked-page filtering, summary generation, and JSON output.

- [ ] **Step 6: Commit the auth CLI and orchestration**

```bash
git add tests/skills/test_playwright_auth_login.py \
  optional-skills/communication/playwright-auth-login/scripts/playwright_auth_login.py
git commit -m "feat: add playwright auth login cli"
```

### Task 5: Add skill metadata and update page-capture documentation

**Files:**
- Create: `optional-skills/communication/playwright-auth-login/DESCRIPTION.md`
- Create: `optional-skills/communication/playwright-auth-login/SKILL.md`
- Modify: `optional-skills/communication/playwright-page-capture/SKILL.md`
- Modify: `tests/skills/test_playwright_auth_login.py`

- [ ] **Step 1: Write the failing scaffold test for the new skill docs**

```python
def test_playwright_auth_login_skill_scaffold_exists() -> None:
    root = REPO_ROOT / "optional-skills" / "communication" / "playwright-auth-login"
    assert (root / "DESCRIPTION.md").exists()
    assert (root / "SKILL.md").exists()
    assert (root / "scripts" / "playwright_auth_login.py").exists()
```

- [ ] **Step 2: Run the scaffold test to verify it fails**

Run: `pytest tests/skills/test_playwright_auth_login.py::test_playwright_auth_login_skill_scaffold_exists -v`
Expected: FAIL because the skill folder and docs are not created yet.

- [ ] **Step 3: Write the new skill description file**

```markdown
# Playwright Auth Login

Playwright 自动登录 skill，基于 `~/.hermes/playwright-auth.yaml` 的站点适配配置执行账号密码登录，并可在成功后串联运行关联的 `playwright-page-capture` 页面抓取。

**安装方式：**
```bash
hermes skills install official/communication/playwright-auth-login
```

**依赖：** `playwright`（会自动提示安装 Chromium）
```

- [ ] **Step 4: Write the new skill guide and update page-capture docs**

```markdown
# Playwright Auth Login

```bash
/playwright-auth-login site_id=feishu_admin
/playwright-auth-login site_id=feishu_admin --run-linked-pages
```

配置文件：`~/.hermes/playwright-auth.yaml`

`playwright-page-capture.yaml` 中可通过 `auth_site_id` 关联登录站点；启用 `--run-linked-pages` 后，会自动运行所有匹配的 `page_id`。
```

Add this block to `optional-skills/communication/playwright-page-capture/SKILL.md` near the storage-state section:

```markdown
### 与 playwright-auth-login 联动

若页面依赖自动登录站点，可在页面配置中增加：

```yaml
pages:
  - page_id: dashboard_main
    auth_site_id: feishu_admin
```

然后执行：

```bash
/playwright-auth-login site_id=feishu_admin --run-linked-pages
```
```

- [ ] **Step 5: Run the documentation/scaffold tests to verify they pass**

Run: `pytest tests/skills/test_playwright_auth_login.py -v`
Expected: PASS for scaffold existence and previously added CLI tests.

- [ ] **Step 6: Commit the skill docs**

```bash
git add tests/skills/test_playwright_auth_login.py \
  optional-skills/communication/playwright-auth-login/DESCRIPTION.md \
  optional-skills/communication/playwright-auth-login/SKILL.md \
  optional-skills/communication/playwright-page-capture/SKILL.md
git commit -m "docs: add playwright auth login skill metadata"
```

### Task 6: Run the full targeted test suite and polish result handling

**Files:**
- Modify: `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_login.py`
- Modify: `optional-skills/communication/playwright-auth-login/scripts/playwright_auth_runner.py`
- Modify: `tests/skills/test_playwright_auth_login.py`
- Modify: `tests/skills/test_playwright_auth_runner.py`

- [ ] **Step 1: Add a failing regression test for “login success with no linked pages”**

```python
def test_main_returns_empty_linked_pages_when_no_matches(monkeypatch, capsys):
    monkeypatch.setattr(module, "_default_auth_config_path", lambda: Path("/tmp/auth.yaml"))
    monkeypatch.setattr(module, "_default_capture_config_path", lambda: Path("/tmp/capture.yaml"))
    monkeypatch.setattr(module, "load_playwright_auth_config", lambda path: PlaywrightAuthConfig(sites=[SITE]))
    monkeypatch.setattr(module, "run_auth_flow", lambda site: {
        "status": "success",
        "site_id": site.site_id,
        "storage_state_path": "/tmp/feishu_admin.js",
    })
    monkeypatch.setattr(module, "run_linked_pages", lambda **kwargs: [])

    monkeypatch.setattr(sys, "argv", ["playwright_auth_login.py", "--site-id", "feishu_admin", "--run-linked-pages"])
    module.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["linked_pages"] == []
    assert payload["capture_summary"] == {"total": 0, "ok": 0, "failed": 0}
```

- [ ] **Step 2: Run the focused regression tests to verify they fail first**

Run: `pytest tests/skills/test_playwright_auth_login.py::test_main_returns_empty_linked_pages_when_no_matches tests/skills/test_playwright_auth_runner.py -v`
Expected: FAIL if empty-linked-page summary or runner edge handling is missing.

- [ ] **Step 3: Tighten result handling for empty linked pages and runner cleanup**

```python
if args.run_linked_pages:
    linked_pages = run_linked_pages(...)
    result["linked_pages"] = linked_pages
    result["capture_summary"] = summarize_linked_pages(linked_pages)
```

```python
try:
    page.goto(site.login_url, wait_until="domcontentloaded", timeout=30000)
    ...
finally:
    context.close()
    browser.close()
```

Keep the cleanup in the runner even for `step_failed` / `login_failed`, and ensure `summarize_linked_pages([])` returns zeros.

- [ ] **Step 4: Run the complete targeted suite**

Run: `pytest tests/skills/test_playwright_auth_config.py tests/skills/test_playwright_auth_runner.py tests/skills/test_playwright_auth_login.py tests/skills/test_playwright_page_capture_config.py -v`
Expected: PASS for all new auth tests and the updated page-capture config coverage.

- [ ] **Step 5: Run one existing page-capture smoke suite to verify no regression**

Run: `pytest tests/skills/test_playwright_page_capture.py -v`
Expected: PASS, confirming the new `auth_site_id` field did not break the existing skill behavior.

- [ ] **Step 6: Commit the verification and polish changes**

```bash
git add tests/skills/test_playwright_auth_config.py \
  tests/skills/test_playwright_auth_runner.py \
  tests/skills/test_playwright_auth_login.py \
  tests/skills/test_playwright_page_capture_config.py \
  optional-skills/communication/playwright-auth-login/scripts/playwright_auth_login.py \
  optional-skills/communication/playwright-auth-login/scripts/playwright_auth_runner.py
git commit -m "test: verify playwright auth login flow"
```

---

## Self-Review

### Spec coverage
- New formal skill with visible docs: Tasks 4-5
- Separate `playwright-auth.yaml` config with username/password and steps: Task 2
- Basic supported actions (`fill`, `click`, `wait_for_selector`, `wait_for_url`): Task 3
- Save `storage_state` on successful login: Task 3
- Add `auth_site_id` to page-capture config: Task 1
- `--run-linked-pages` orchestration and reuse of capture/Feishu flow: Task 4
- Structured statuses (`success`, `login_failed`, `step_failed`, `config_error`/error paths) and empty-linked-page handling: Tasks 3, 4, and 6
- Keep first version scoped without MFA/captcha/generalized heuristics: enforced by Task 2/3 model design and omitted functionality

### Placeholder scan
- No TBD/TODO markers left in tasks.
- Each code-edit step includes explicit snippets, commands, and expected outcomes.
- Test commands are concrete and map to real file paths.

### Type consistency
- `auth_site_id` is added consistently to `PageCaptureDefinition`, YAML parsing, and linked-page filtering.
- Auth config types (`AuthStep`, `AuthSuccessCriteria`, `AuthSiteDefinition`, `PlaywrightAuthConfig`) are referenced consistently across Tasks 2-6.
- `run_linked_pages()` / `summarize_linked_pages()` names are reused consistently in CLI tasks and tests.
