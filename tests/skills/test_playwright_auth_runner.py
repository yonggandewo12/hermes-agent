import sys
from pathlib import Path
import importlib.util
import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "optional-skills"
    / "communication"
    / "playwright-auth-login"
    / "scripts"
)

def load_runner_module():
    # Load playwright_auth_models first
    sys.path.insert(0, str(SCRIPTS_DIR))
    models_spec = importlib.util.spec_from_file_location("playwright_auth_models", SCRIPTS_DIR / "playwright_auth_models.py")
    models_module = importlib.util.module_from_spec(models_spec)
    sys.modules["playwright_auth_models"] = models_module
    models_spec.loader.exec_module(models_module)

    runner_spec = importlib.util.spec_from_file_location("playwright_auth_runner", SCRIPTS_DIR / "playwright_auth_runner.py")
    runner_module = importlib.util.module_from_spec(runner_spec)
    sys.modules["playwright_auth_runner"] = runner_module
    runner_spec.loader.exec_module(runner_module)
    return runner_module


def test_run_auth_flow_executes_steps_and_saves_storage_state(tmp_path: Path):
    """Mock-based test: runner executes fill/click/wait_for_url steps and returns success."""
    module = load_runner_module()

    # Dummy classes that mimic the playwright API.
    # The runner calls: browser = pw.chromium.launch()
    #                   context = browser.new_context()
    #                   page = context.new_page()
    # We use __getattribute__ on DummyPlaywright so .chromium returns
    # a DummyBrowser directly (not a bound method).

    class DummyPage:
        def __init__(self):
            self.actions = []
            self._url = "https://example.com/home"

        @property
        def url(self):
            return self._url

        def goto(self, url, wait_until=None, timeout=None):
            self.actions.append(("goto", url))

        def fill(self, selector, value):
            self.actions.append(("fill", selector, value))

        def click(self, selector):
            self.actions.append(("click", selector))

        def wait_for_url(self, url_pattern):
            self.actions.append(("wait_for_url_not_contains", "/login"))

    class DummyContext:
        def __init__(self, page, cookies_list):
            self._page = page
            self._cookies = cookies_list

        def cookies(self):
            return self._cookies

        def storage_state(self, path=None):
            pass

        def new_page(self):
            return self._page

        def close(self):
            pass

    class DummyBrowser:
        def __init__(self, context):
            self._context = context

        def new_context(self):
            return self._context

        def launch(self, **kwargs):
            return self

        def close(self):
            pass

    class DummyPlaywright:
        def __init__(self, page, context):
            self._page = page
            self._context = context
            self._browser = DummyBrowser(context)

        def __getattribute__(self, name):
            if name == "chromium":
                return super().__getattribute__("_browser")
            return super().__getattribute__(name)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    page = DummyPage()
    context = DummyContext(page, [{"name": "session_id"}])

    site = module.AuthSiteDefinition(
        site_id="feishu_admin",
        name="Feishu Admin",
        login_url="https://example.com/login",
        username="demo_user",
        password="demo_pass",
        storage_state_path="feishu/feishu_admin.js",
        steps=[
            module.AuthStep(action="fill", selector="input[name='username']", value_from="username"),
            module.AuthStep(action="fill", selector="input[name='password']", value_from="password"),
            module.AuthStep(action="click", selector="button[type='submit']"),
            module.AuthStep(action="wait_for_url", url_not_contains="/login"),
        ],
        success_criteria=module.AuthSuccessCriteria(url_not_contains=["/login"], cookie_names=["session"]),
    )

    result = module.run_auth_flow(site, playwright_factory=lambda: DummyPlaywright(page, context))

    assert result["status"] == "success"
    assert result["site_id"] == "feishu_admin"
    assert result["storage_state_path"].endswith("feishu/feishu_admin.js")
    assert ("goto", "https://example.com/login") in page.actions
    assert ("fill", "input[name='username']", "demo_user") in page.actions
    assert ("fill", "input[name='password']", "demo_pass") in page.actions


def test_run_auth_flow_returns_step_failed_for_missing_selector(tmp_path: Path):
    """Mock-based test: runner returns step_failed when a selector is not found."""
    module = load_runner_module()

    class DummyPage:
        def goto(self, url, wait_until=None, timeout=None):
            pass

        def click(self, selector):
            if selector == "button.missing":
                raise Exception("selector not found: button.missing")

    class DummyContext:
        def __init__(self, page):
            self._page = page

        def cookies(self):
            return []
        def storage_state(self, path=None):
            pass
        def new_page(self):
            return self._page
        def close(self):
            pass

    class DummyBrowser:
        def __init__(self, context):
            self._context = context

        def new_context(self):
            return self._context
        def launch(self, **kwargs):
            return self
        def close(self):
            pass

    class DummyPlaywright:
        def __init__(self):
            page = DummyPage()
            context = DummyContext(page)
            self._browser = DummyBrowser(context)

        def __getattribute__(self, name):
            if name == "chromium":
                return super().__getattribute__("_browser")
            return super().__getattribute__(name)

        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    site = module.AuthSiteDefinition(
        site_id="broken",
        name="Broken",
        login_url="https://example.com/login",
        username="demo_user",
        password="demo_pass",
        storage_state_path="broken.js",
        steps=[module.AuthStep(action="click", selector="button.missing")],
        success_criteria=module.AuthSuccessCriteria(),
    )

    result = module.run_auth_flow(site, playwright_factory=lambda: DummyPlaywright())

    assert result["status"] == "step_failed"
    assert result["site_id"] == "broken"
    assert result["failed_step"] == 1
    assert "button.missing" in result["error"]


def test_run_auth_flow_returns_login_failed_when_criteria_not_met(tmp_path: Path):
    """Mock-based test: all steps succeed but success_criteria not met -> login_failed."""
    module = load_runner_module()

    class DummyPage:
        def __init__(self):
            self.actions = []
            self._url = "https://example.com/login"  # Still on login page

        @property
        def url(self):
            return self._url

        def goto(self, url, wait_until=None, timeout=None):
            self.actions.append(("goto", url))

        def fill(self, selector, value):
            self.actions.append(("fill", selector, value))

        def click(self, selector):
            self.actions.append(("click", selector))

    class DummyContext:
        def __init__(self, page):
            self._page = page

        def cookies(self):
            return []  # No session cookie

        def storage_state(self, path=None):
            pass

        def new_page(self):
            return self._page

        def close(self):
            pass

    class DummyBrowser:
        def __init__(self, context):
            self._context = context

        def new_context(self):
            return self._context
        def launch(self, **kwargs):
            return self
        def close(self):
            pass

    class DummyPlaywright:
        def __init__(self):
            page = DummyPage()
            context = DummyContext(page)
            self._browser = DummyBrowser(context)

        def __getattribute__(self, name):
            if name == "chromium":
                return super().__getattribute__("_browser")
            return super().__getattribute__(name)

        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    site = module.AuthSiteDefinition(
        site_id="no_session",
        name="No Session",
        login_url="https://example.com/login",
        username="user",
        password="pass",
        storage_state_path="no_session.js",
        steps=[
            module.AuthStep(action="fill", selector="input[name='username']", value_from="username"),
            module.AuthStep(action="fill", selector="input[name='password']", value_from="password"),
            module.AuthStep(action="click", selector="button[type='submit']"),
        ],
        success_criteria=module.AuthSuccessCriteria(url_not_contains=["/login"], cookie_names=["session"]),
    )

    result = module.run_auth_flow(site, playwright_factory=lambda: DummyPlaywright())

    assert result["status"] == "login_failed"
    assert result["site_id"] == "no_session"
