# Hermes Setup Playwright Page Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `hermes setup` 的 tools 阶段为 `playwright-page-capture` 提供正式的一次性配置入口，并将配置统一写入 `~/.hermes/playwright-page-capture.yaml`。

**Architecture:** 方案在 `hermes_cli/tools_config.py` 中把当前简陋的 Feishu 凭证 prompt 升级为一个专项配置向导。该向导负责读取/更新 `~/.hermes/playwright-page-capture.yaml`，支持首次创建、仅更新 Feishu 凭证、以及可选追加一个最小 page 示例，同时保持 skill 运行时默认读取该文件，不再把此能力混入 gateway 平台配置。

**Tech Stack:** Python 3.11, Hermes CLI setup flow, PyYAML, pytest, existing Hermes config helpers

---

## File Structure

### Existing files to modify
- `hermes_cli/tools_config.py` — 在 first-install tools 流程中新增 `playwright-page-capture` 专项 setup 向导；封装 YAML 读写、现有配置分支处理、示例 page 追加与完成提示。
- `tests/skills/test_playwright_page_capture_config.py` — 增加针对新 setup helper 的 YAML 写入/合并行为测试。
- `README.zh-CN.md` — 将用户可见的正式配置路径说明为 `hermes setup -> tools` 与 `~/.hermes/playwright-page-capture.yaml`。
- `README.md` — 同步英文说明，避免文档继续暗示错误入口。

### Existing files to inspect while implementing
- `optional-skills/communication/playwright-page-capture/scripts/page_capture_config.py` — 确认 YAML 结构必须兼容现有 loader。
- `optional-skills/communication/playwright-page-capture/examples/page-capture.example.yaml` — 复用现有 page 字段命名，确保 setup 生成的示例配置可直接运行。
- `hermes_cli/setup.py` — 确认不再把 skill 配置误导为 gateway 配置入口；若当前工作树有临时 Feishu gateway 变更，需回退或避免在计划外继续扩散。

---

### Task 1: 为 Playwright Page Capture setup 抽出可测试的 YAML helper

**Files:**
- Modify: `hermes_cli/tools_config.py`
- Test: `tests/skills/test_playwright_page_capture_config.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from hermes_cli import tools_config


def test_write_playwright_page_capture_config_creates_feishu_section(tmp_path, monkeypatch):
    target = tmp_path / "playwright-page-capture.yaml"
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    tools_config._write_playwright_page_capture_config(
        app_id="cli_test",
        app_secret="secret_test",
    )

    content = target.read_text(encoding="utf-8")
    assert "feishu:" in content
    assert "app_id: cli_test" in content
    assert "app_secret: secret_test" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_write_playwright_page_capture_config_creates_feishu_section -v`
Expected: FAIL with `AttributeError` because `_playwright_page_capture_config_path` / `_write_playwright_page_capture_config` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

`hermes_cli/tools_config.py`

```python
from pathlib import Path
import yaml


def _playwright_page_capture_config_path() -> Path:
    return Path.home() / ".hermes" / "playwright-page-capture.yaml"


def _load_playwright_page_capture_config() -> dict:
    path = _playwright_page_capture_config_path()
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_playwright_page_capture_config(*, app_id: str, app_secret: str) -> Path:
    path = _playwright_page_capture_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_playwright_page_capture_config()
    existing.setdefault("feishu", {})["app_id"] = app_id
    existing.setdefault("feishu", {})["app_secret"] = app_secret
    path.write_text(yaml.dump(existing, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_write_playwright_page_capture_config_creates_feishu_section -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hermes_cli/tools_config.py tests/skills/test_playwright_page_capture_config.py
git commit -m "refactor: extract playwright page capture config helpers"
```

---

### Task 2: 让 helper 在已有配置上做非破坏性更新

**Files:**
- Modify: `hermes_cli/tools_config.py`
- Test: `tests/skills/test_playwright_page_capture_config.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

import yaml
from hermes_cli import tools_config


def test_write_playwright_page_capture_config_preserves_existing_pages(tmp_path, monkeypatch):
    target = tmp_path / "playwright-page-capture.yaml"
    target.write_text(
        yaml.dump(
            {
                "pages": [
                    {
                        "page_id": "baidu_poc",
                        "name": "百度",
                        "url": "https://www.baidu.com",
                        "feishu_target": {"chat_id": "oc_old"},
                    }
                ]
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    tools_config._write_playwright_page_capture_config(
        app_id="cli_new",
        app_secret="secret_new",
    )

    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert loaded["pages"][0]["page_id"] == "baidu_poc"
    assert loaded["feishu"]["app_id"] == "cli_new"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_write_playwright_page_capture_config_preserves_existing_pages -v`
Expected: FAIL if helper overwrites the file or drops `pages`.

- [ ] **Step 3: Write minimal implementation**

Ensure `_write_playwright_page_capture_config()` keeps all existing top-level keys and only updates the nested `feishu` section.

```python
def _write_playwright_page_capture_config(*, app_id: str, app_secret: str) -> Path:
    path = _playwright_page_capture_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_playwright_page_capture_config()
    feishu = existing.setdefault("feishu", {})
    feishu["app_id"] = app_id
    feishu["app_secret"] = app_secret
    path.write_text(yaml.dump(existing, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_write_playwright_page_capture_config_preserves_existing_pages -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hermes_cli/tools_config.py tests/skills/test_playwright_page_capture_config.py
git commit -m "test: preserve existing page capture yaml entries"
```

---

### Task 3: 为 setup 向导增加可选示例 page 追加能力

**Files:**
- Modify: `hermes_cli/tools_config.py`
- Test: `tests/skills/test_playwright_page_capture_config.py`

- [ ] **Step 1: Write the failing test**

```python
import yaml
from hermes_cli import tools_config


def test_append_playwright_page_capture_page_adds_minimal_page(tmp_path, monkeypatch):
    target = tmp_path / "playwright-page-capture.yaml"
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)
    tools_config._write_playwright_page_capture_config(app_id="cli_test", app_secret="secret_test")

    tools_config._append_playwright_page_capture_page(
        page_id="baidu_poc",
        name="百度搜索 PoC",
        url="https://www.baidu.com",
        chat_id="oc_xxx",
    )

    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    page = loaded["pages"][0]
    assert page["page_id"] == "baidu_poc"
    assert page["wait_for"]["load_state"] == "networkidle"
    assert page["feishu_target"]["chat_id"] == "oc_xxx"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_append_playwright_page_capture_page_adds_minimal_page -v`
Expected: FAIL with `AttributeError` because `_append_playwright_page_capture_page` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

`hermes_cli/tools_config.py`

```python
def _append_playwright_page_capture_page(*, page_id: str, name: str, url: str, chat_id: str) -> Path:
    path = _playwright_page_capture_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_playwright_page_capture_config()
    pages = existing.setdefault("pages", [])
    pages.append(
        {
            "page_id": page_id,
            "name": name,
            "url": url,
            "wait_for": {
                "load_state": "networkidle",
            },
            "feishu_target": {
                "chat_id": chat_id,
            },
        }
    )
    path.write_text(yaml.dump(existing, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_append_playwright_page_capture_page_adds_minimal_page -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hermes_cli/tools_config.py tests/skills/test_playwright_page_capture_config.py
git commit -m "feat: add page capture example page writer"
```

---

### Task 4: 把 first-install prompt 升级成完整 setup 向导

**Files:**
- Modify: `hermes_cli/tools_config.py`
- Test: `tests/skills/test_playwright_page_capture_config.py`

- [ ] **Step 1: Write the failing test**

```python
from hermes_cli import tools_config


def test_setup_playwright_page_capture_prompts_for_example_page(monkeypatch, tmp_path):
    target = tmp_path / "playwright-page-capture.yaml"
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    answers = iter([
        "y",              # configure skill
        "cli_test",       # app id
        "secret_test",    # app secret
        "y",              # create example page
        "baidu_poc",      # page id
        "百度搜索 PoC",     # name
        "https://www.baidu.com",  # url
        "oc_xxx",         # chat id
    ])
    monkeypatch.setattr(tools_config, "_prompt", lambda *args, **kwargs: next(answers))

    path = tools_config._setup_playwright_page_capture()

    assert path == target
    assert target.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_setup_playwright_page_capture_prompts_for_example_page -v`
Expected: FAIL with `AttributeError` because `_setup_playwright_page_capture` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

`hermes_cli/tools_config.py`

```python
def _setup_playwright_page_capture() -> Path | None:
    if _prompt("Configure Playwright Page Capture?", default="n").lower() != "y":
        return None

    app_id = _prompt("  Feishu App ID")
    app_secret = _prompt("  Feishu App Secret", password=True)
    if not app_id or not app_secret:
        _print_warning("Skipped Playwright Page Capture setup because Feishu credentials were incomplete")
        return None

    path = _write_playwright_page_capture_config(app_id=app_id, app_secret=app_secret)

    if _prompt("  Create an example page entry?", default="y").lower() == "y":
        page_id = _prompt("    page_id", default="baidu_poc") or "baidu_poc"
        name = _prompt("    name", default="百度搜索 PoC") or "百度搜索 PoC"
        url = _prompt("    url", default="https://www.baidu.com") or "https://www.baidu.com"
        chat_id = _prompt("    Feishu chat_id")
        if chat_id:
            path = _append_playwright_page_capture_page(
                page_id=page_id,
                name=name,
                url=url,
                chat_id=chat_id,
            )

    _print_success(f"Saved Playwright Page Capture config to {path}")
    print("Run with: hermes -q \"使用 playwright-page-capture 处理 page_id=baidu_poc\"")
    return path
```

- [ ] **Step 4: Wire the new helper into first-install flow**

Replace the current block at `hermes_cli/tools_config.py:1400-1420`:

```python
        _setup_playwright_page_capture()
        return
```

instead of manually prompting and writing inline YAML there.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_setup_playwright_page_capture_prompts_for_example_page -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add hermes_cli/tools_config.py tests/skills/test_playwright_page_capture_config.py
git commit -m "feat: add first-install page capture setup wizard"
```

---

### Task 5: 处理已有配置文件时的分支行为

**Files:**
- Modify: `hermes_cli/tools_config.py`
- Test: `tests/skills/test_playwright_page_capture_config.py`

- [ ] **Step 1: Write the failing test**

```python
import yaml
from hermes_cli import tools_config


def test_setup_playwright_page_capture_updates_feishu_without_removing_existing_pages(monkeypatch, tmp_path):
    target = tmp_path / "playwright-page-capture.yaml"
    target.write_text(
        yaml.dump(
            {
                "feishu": {"app_id": "old", "app_secret": "old_secret"},
                "pages": [{"page_id": "existing", "name": "Existing", "url": "https://example.com", "feishu_target": {"chat_id": "oc_old"}}],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    answers = iter([
        "y",           # configure skill
        "u",           # update feishu only
        "cli_new",
        "secret_new",
    ])
    monkeypatch.setattr(tools_config, "_prompt", lambda *args, **kwargs: next(answers))

    tools_config._setup_playwright_page_capture()

    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert loaded["feishu"]["app_id"] == "cli_new"
    assert loaded["pages"][0]["page_id"] == "existing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_setup_playwright_page_capture_updates_feishu_without_removing_existing_pages -v`
Expected: FAIL because the setup helper does not yet branch on existing config.

- [ ] **Step 3: Write minimal implementation**

Extend `_setup_playwright_page_capture()` to detect an existing file and offer a simple branch prompt:

```python
    existing = _load_playwright_page_capture_config()
    if existing:
        action = (_prompt("  Existing config found: [k]eep, [u]pdate Feishu, [a]ppend page", default="u") or "u").lower()
        if action == "k":
            _print_success(f"Keeping existing Playwright Page Capture config at {path}")
            return _playwright_page_capture_config_path()
        if action == "a":
            chat_id = _prompt("    Feishu chat_id")
            if chat_id:
                return _append_playwright_page_capture_page(
                    page_id=_prompt("    page_id", default="baidu_poc") or "baidu_poc",
                    name=_prompt("    name", default="百度搜索 PoC") or "百度搜索 PoC",
                    url=_prompt("    url", default="https://www.baidu.com") or "https://www.baidu.com",
                    chat_id=chat_id,
                )
```

Then keep the `u` path as the default branch that updates only Feishu credentials.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/skills/test_playwright_page_capture_config.py::test_setup_playwright_page_capture_updates_feishu_without_removing_existing_pages -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hermes_cli/tools_config.py tests/skills/test_playwright_page_capture_config.py
git commit -m "feat: handle existing page capture setup config"
```

---

### Task 6: 更新用户文档为唯一正式路径

**Files:**
- Modify: `README.zh-CN.md`
- Modify: `README.md`

- [ ] **Step 1: Write the failing doc expectation as a testable grep check**

Run: `grep -n "hermes setup\|playwright-page-capture.yaml" README.zh-CN.md README.md`
Expected: Current output does not clearly state that the official configuration path is `hermes setup -> tools` and `~/.hermes/playwright-page-capture.yaml`.

- [ ] **Step 2: Update the docs**

`README.zh-CN.md`

```markdown
### Playwright Page Capture Skill

推荐先运行：

```bash
hermes setup
```

在 tools 阶段启用并配置 Playwright Page Capture。配置会写入：

```bash
~/.hermes/playwright-page-capture.yaml
```

完成后运行：

```bash
hermes -q "使用 playwright-page-capture 处理 page_id=baidu_poc"
```
```

`README.md`

```markdown
### Playwright Page Capture Skill

Recommended setup path:

```bash
hermes setup
```

Enable and configure Playwright Page Capture during the tools step. The configuration is written to:

```bash
~/.hermes/playwright-page-capture.yaml
```

Then run:

```bash
hermes -q "Use playwright-page-capture to process page_id=baidu_poc"
```
```

- [ ] **Step 3: Re-run the grep check**

Run: `grep -n "hermes setup\|playwright-page-capture.yaml" README.zh-CN.md README.md`
Expected: Output shows both README files now document `hermes setup` and `~/.hermes/playwright-page-capture.yaml` together.

- [ ] **Step 4: Commit**

```bash
git add README.zh-CN.md README.md
git commit -m "docs: document setup path for page capture config"
```

---

### Task 7: 验证正式启动路径与回归点

**Files:**
- Modify: `tests/skills/test_playwright_page_capture_config.py`
- Inspect: `optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py`

- [ ] **Step 1: Add a regression test for the final config shape**

```python
import yaml
from hermes_cli import tools_config


def test_setup_playwright_page_capture_writes_runtime_compatible_yaml(monkeypatch, tmp_path):
    target = tmp_path / "playwright-page-capture.yaml"
    monkeypatch.setattr(tools_config, "_playwright_page_capture_config_path", lambda: target)

    answers = iter([
        "y",
        "cli_test",
        "secret_test",
        "y",
        "baidu_poc",
        "百度搜索 PoC",
        "https://www.baidu.com",
        "oc_xxx",
    ])
    monkeypatch.setattr(tools_config, "_prompt", lambda *args, **kwargs: next(answers))

    tools_config._setup_playwright_page_capture()

    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert loaded["feishu"]["app_id"] == "cli_test"
    assert loaded["pages"][0]["name"] == "百度搜索 PoC"
    assert loaded["pages"][0]["feishu_target"]["chat_id"] == "oc_xxx"
```

- [ ] **Step 2: Run focused tests**

Run: `pytest tests/skills/test_playwright_page_capture_config.py -v`
Expected: PASS

- [ ] **Step 3: Run one broader regression slice**

Run: `pytest tests/skills/test_playwright_page_capture.py tests/skills/test_playwright_page_capture_config.py -v`
Expected: PASS

- [ ] **Step 4: Manual verification checklist**

Run in an interactive terminal:

```bash
hermes setup
```

Expected manual path:
1. Reach the tools step.
2. See the Playwright Page Capture configuration prompt.
3. Enter Feishu App ID / App Secret.
4. Optionally create a sample page.
5. Confirm file exists at `~/.hermes/playwright-page-capture.yaml`.
6. Run:

```bash
hermes -q "使用 playwright-page-capture 处理 page_id=baidu_poc"
```

Expected: Hermes loads the default config path and dispatches the skill using the generated YAML config.

- [ ] **Step 5: Commit**

```bash
git add tests/skills/test_playwright_page_capture_config.py
git commit -m "test: verify page capture setup output shape"
```

---

## Self-Review

- **Spec coverage:** 已覆盖 setup tools 集成、唯一配置文件路径、已有文件分支、可选示例 page、文档与最终运行路径验证。
- **Placeholder scan:** 无 `TODO` / `TBD` / “类似 Task N” 占位表达；每个代码步骤都给出明确路径和代码。
- **Type consistency:** helper 名称统一为 `_playwright_page_capture_config_path`、`_load_playwright_page_capture_config`、`_write_playwright_page_capture_config`、`_append_playwright_page_capture_page`、`_setup_playwright_page_capture`；YAML 字段名与现有 loader 使用的 `feishu` / `pages` / `feishu_target.chat_id` 保持一致。
