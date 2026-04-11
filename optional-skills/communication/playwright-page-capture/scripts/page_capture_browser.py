from __future__ import annotations


def build_browser_launch_options(storage_state_path: str | None) -> dict[str, object]:
    return {
        "headless": True,
        "storage_state": storage_state_path,
    }


def normalize_runtime_result(*, page, events, fetch_error: str | None, login_required: bool, dom_result=None) -> dict[str, object]:
    return {
        "page": page,
        "events": events,
        "fetch_error": fetch_error,
        "login_required": login_required,
        "dom_result": dom_result,
    }


def run_browser_capture(page_def):
    from playwright.sync_api import sync_playwright

    try:
        from .page_capture_dom import extract_dom_fields
    except ImportError:
        from page_capture_dom import extract_dom_fields

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
            dom_result = extract_dom_fields(page, page_def.dom_fields)
            return normalize_runtime_result(
                page=None,
                events=events,
                fetch_error=None,
                login_required=False,
                dom_result=dom_result,
            )
        except Exception as exc:
            return normalize_runtime_result(page=None, events=events, fetch_error=str(exc), login_required=False)
        finally:
            context.close()
            browser.close()