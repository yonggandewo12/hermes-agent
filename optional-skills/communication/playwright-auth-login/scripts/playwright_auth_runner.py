from pathlib import Path

from playwright_auth_models import (
    AuthSiteDefinition,
    AuthStep,
    AuthSuccessCriteria,
    resolve_auth_storage_state_path,
)


def _step_value(site: AuthSiteDefinition, value_from: str | None) -> str:
    if value_from == "username":
        return site.username
    if value_from == "password":
        return site.password
    raise ValueError(f"Unsupported value_from: {value_from}")


def _run_step(page, site: AuthSiteDefinition, step: AuthStep) -> None:
    # Supported actions: fill, click, press, wait_for_selector, wait_for_url
    if step.action == "fill":
        page.fill(step.selector, _step_value(site, step.value_from))
        return
    if step.action == "click":
        page.click(step.selector)
        return
    if step.action == "wait_for_selector":
        page.wait_for_selector(step.selector)
        return
    if step.action == "press":
        page.press(step.selector or "body", step.value_from or "Enter")
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


def run_auth_flow(site: AuthSiteDefinition, playwright_factory=None) -> dict[str, object]:
    from playwright.sync_api import sync_playwright

    if playwright_factory is None:
        playwright_factory = sync_playwright

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
