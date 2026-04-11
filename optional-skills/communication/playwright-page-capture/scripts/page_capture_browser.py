from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


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


def run_browser_snapshot(
    url: str,
    storage_state_path: str | None = None,
    *,
    wait_for_load: str = "domcontentloaded",
    selector: str | None = None,
    output_format: str = "html",  # "html" | "json"
) -> dict[str, object]:
    """
    Navigate to *url* and return the full page snapshot (HTML / structured DOM).

    Supports storage_state for authenticated pages.  No Feishu dependency.

    Args:
        url: Target URL.
        storage_state_path: Optional auth state (absolute or relative → ~/.hermes/stats/).
        wait_for_load: Playwright load state ("domcontentloaded", "load", "networkidle").
        selector: Optional selector to wait for before capturing.
        output_format: "html" → raw page HTML; "json" → structured element tree.

    Returns:
        {
            "status": "ok"|"error"|"login_required",
            "url": final_url,
            "title": page_title,
            "html": full_page_html,          # always present on ok
            "elements": [...],                # only when output_format="json"
            "screenshot": "/tmp/...png",      # path to screenshot
            "error": "..."                    # only on error
        }
    """
    # Resolve storage_state path
    resolved_storage = None
    if storage_state_path:
        try:
            from page_capture_models import resolve_storage_state_path
        except ImportError:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from page_capture_models import resolve_storage_state_path
        resolved_storage = resolve_storage_state_path(storage_state_path)
        if resolved_storage and not os.path.exists(resolved_storage):
            resolved_storage = None

    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    context_kwargs = {}
    if resolved_storage:
        context_kwargs["storage_state"] = resolved_storage

    result: dict[str, object] = {
        "status": "error",
        "url": url,
        "title": "",
        "html": "",
        "elements": [],
        "screenshot": "",
        "error": "",
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        try:
            page.goto(url, wait_until=wait_for_load, timeout=30000)
        except PlaywrightTimeout:
            result["error"] = f"Page load timeout after 30s: {url}"
            context.close()
            browser.close()
            return result
        except Exception as exc:
            result["error"] = f"Navigation failed: {exc}"
            context.close()
            browser.close()
            return result

        # Wait for optional selector
        if selector:
            try:
                page.wait_for_selector(selector, timeout=15000)
            except Exception:
                pass  # non-fatal

        result["url"] = page.url
        result["title"] = page.title()

        # Full HTML
        result["html"] = page.content()

        # Screenshot to temp file
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png", prefix="snapshot_")
        os.close(tmp_fd)
        page.screenshot(path=tmp_path, full_page=True)
        result["screenshot"] = tmp_path

        # Structured elements (simplified DOM tree) when json format requested
        if output_format == "json":
            result["elements"] = _extract_element_tree(page)

        result["status"] = "ok"

        context.close()
        browser.close()
        return result


def _extract_element_tree(page) -> list[dict]:
    """Extract a simplified DOM element tree from the page."""
    try:
        return page.evaluate("""
            () => {
                const exclude = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'IFRAME', 'SVG', 'META', 'LINK', 'HEAD']);
                const result = [];
                function walk(el, depth) {
                    if (depth > 4) return;  // limit depth
                    if (exclude.has(el.tagName)) return;
                    const children = Array.from(el.children);
                    result.push({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || undefined,
                        cls: el.className && typeof el.className === 'string' ? el.className.split(' ').filter(Boolean) : undefined,
                        text: el.innerText ? el.innerText.trim().substring(0, 200) : undefined,
                        href: el.href || undefined,
                        src: el.src || undefined,
                        children: children.length,
                    });
                    children.forEach(c => walk(c, depth + 1));
                }
                document.body && document.body.children && Array.from(document.body.children).forEach(c => walk(c, 0));
                return result;
            }
        """)
    except Exception:
        return []


def run_browser_capture(page_def):
    from playwright.sync_api import sync_playwright

    try:
        from .page_capture_dom import extract_dom_fields
        from .page_capture_models import resolve_storage_state_path
    except ImportError:
        from page_capture_dom import extract_dom_fields
        from page_capture_models import resolve_storage_state_path

    events: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context_kwargs = {}
        resolved_storage_path = resolve_storage_state_path(page_def.storage_state_path)
        if resolved_storage_path:
            context_kwargs["storage_state"] = resolved_storage_path
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