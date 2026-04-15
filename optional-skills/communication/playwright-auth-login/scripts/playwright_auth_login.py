from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Add page-capture scripts dir to path for cross-module imports
CAPTURE_SCRIPTS_DIR = SCRIPTS_DIR.parent.parent / "playwright-page-capture" / "scripts"
if str(CAPTURE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(CAPTURE_SCRIPTS_DIR))

try:
    from playwright_auth_config import load_playwright_auth_config
    from playwright_auth_models import PlaywrightAuthConfig, AuthSiteDefinition
    from playwright_auth_runner import run_auth_flow
except ImportError:
    from playwright_auth_config import load_playwright_auth_config
    from playwright_auth_models import PlaywrightAuthConfig, AuthSiteDefinition
    from playwright_auth_runner import run_auth_flow


def _default_auth_config_path() -> Path:
    return Path.home() / ".hermes" / "playwright-auth.yaml"


def _default_capture_config_path() -> Path:
    return Path.home() / ".hermes" / "playwright-page-capture.yaml"


def run_linked_pages(*, capture_config_path: str, site_id: str, storage_state_path: str, feishu_client, browser_runner, capture_runner) -> list[dict]:
    from page_capture_config import load_page_capture_config
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


def summarize_linked_pages(results: list[dict]) -> dict[str, int]:
    failed_statuses = {"fetch_failed", "field_missing", "login_required"}
    return {
        "total": len(results),
        "ok": sum(1 for item in results if item["status"] == "ok"),
        "failed": sum(1 for item in results if item["status"] in failed_statuses),
    }


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
    try:
        site = next(s for s in auth_config.sites if s.site_id == args.site_id)
    except StopIteration:
        result = {
            "status": "config_error",
            "error": f"site_id '{args.site_id}' not found in config",
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    result = run_auth_flow(site)
    if result["status"] != "success":
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.run_linked_pages:
        from page_capture_browser import run_browser_capture
        from run_page_capture import build_feishu_client, run_capture_pipeline
        feishu_client = build_feishu_client(capture_config_path)
        linked_pages = run_linked_pages(
            capture_config_path=capture_config_path,
            site_id=site.site_id,
            storage_state_path=result["storage_state_path"],
            feishu_client=feishu_client,
            browser_runner=run_browser_capture,
            capture_runner=run_capture_pipeline,
        )
        result["linked_pages"] = linked_pages
        result["capture_summary"] = summarize_linked_pages(linked_pages)

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
