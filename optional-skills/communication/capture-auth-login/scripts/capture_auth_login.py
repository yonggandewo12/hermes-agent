#!/usr/bin/env python3
"""
capture-auth-login: Interactive login capture script.

Usage (from hermes-agent repo root):
    python optional-skills/communication/capture-auth-login/scripts/capture_auth_login.py --url https://example.com

Usage (from skills directory):
    python scripts/capture_auth_login.py --url https://example.com

Workflow:
    1. Navigate to the URL
    2. Detect if redirected to a login/auth page
    3. If login detected, wait interactively for user to complete login
    4. Save Playwright storage_state to ~/.hermes/stats/{domain}.js
    5. Print success message to stdout
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# URL patterns that indicate a login/auth page
LOGIN_URL_PATTERNS = [
    "/login",
    "/signin",
    "/sign-in",
    "/auth",
    "/oauth",
    "/authorize",
    "/account/login",
    "/accounts/login",
    "/session",
    "/logout",
]

# DOM indicators for login pages
LOGIN_DOM_INDICATORS = [
    "input[type='password']",
    "[name='username']",
    "[name='email']",
    "[name='password']",
    "[id*='login']",
    "[class*='login']",
    "[id*='signin']",
    "[class*='signin']",
    "[id*='password']",
    "[class*='password']",
    'form[action*="login"]',
    'form[action*="signin"]',
]


def _is_login_url(url: str) -> bool:
    parsed = urlparse(url.lower())
    path = parsed.path
    for pattern in LOGIN_URL_PATTERNS:
        if pattern in path:
            return True
    return False


def _has_login_dom(page) -> bool:
    for selector in LOGIN_DOM_INDICATORS:
        try:
            if page.query_selector(selector):
                return True
        except Exception:
            pass
    return False


def _domain_name(url: str) -> str:
    parsed = urlparse(url)
    # Replace dots and slashes with underscores, strip leading/trailing
    name = parsed.netloc.replace(".", "_").replace(":", "_").replace("/", "_")
    # Remove leading/trailing underscores
    name = name.strip("__").replace("__", "_")
    if not name:
        name = parsed.path.replace("/", "_").strip("_")
    return name


def _default_stats_dir() -> Path:
    stats_dir = Path.home() / ".hermes" / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)
    return stats_dir


def _default_output_path(url: str, output_dir: Path | None) -> Path:
    domain = _domain_name(url)
    return (output_dir or _default_stats_dir()) / f"{domain}.js"


def _is_logged_in(page) -> bool:
    """Heuristic: if we're not on a login URL and have cookies, likely logged in."""
    try:
        cookies = page.context.cookies()
        # Look for common session/auth cookie names
        session_cookies = [
            c for c in cookies
            if any(
                name in c["name"].lower()
                for name in ["session", "token", "auth", "logged", "user", "account", "jwt", "access_token"]
            )
        ]
        return len(session_cookies) > 0
    except Exception:
        return False


def run_auth_capture(url: str, output_path: Path | None = None, poll_interval: float = 1.5, timeout: float = 300):
    """
    Navigate to URL, detect login redirect, wait for user to complete login,
    then save storage_state.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    output_path = output_path or _default_output_path(url, None)

    print(f"[capture-auth-login] Navigating to: {url}", file=sys.stderr)
    print(f"[capture-auth-login] Will save storage_state to: {output_path}", file=sys.stderr)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)  # Interactive browser
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            current_url = page.url
            print(f"[capture-auth-login] Initial URL after navigation: {current_url}", file=sys.stderr)

            login_detected = _is_login_url(current_url) or _has_login_dom(page)

            if not login_detected:
                # Wait a bit more for potential redirect
                time.sleep(2)
                current_url = page.url
                login_detected = _is_login_url(current_url) or _has_login_dom(page)
                print(f"[capture-auth-login] URL after wait: {current_url}", file=sys.stderr)

            if not login_detected:
                print(
                    "[capture-auth-login] No login redirect detected. "
                    "Navigating to original URL and saving initial state.",
                    file=sys.stderr,
                )
                context.storage_state(path=str(output_path))
                result = {
                    "status": "no_login_detected",
                    "url": current_url,
                    "output_path": str(output_path),
                }
                print(json.dumps(result, ensure_ascii=False))
                return result

            print(
                "[capture-auth-login] Login page detected! Please complete login in the browser.",
                file=sys.stderr,
            )
            print(
                "[capture-auth-login] Waiting for login completion (max {:.0f}s)...".format(timeout),
                file=sys.stderr,
            )

            # Poll until login is complete or timeout
            start_time = time.time()
            last_url = current_url
            while time.time() - start_time < timeout:
                time.sleep(poll_interval)
                try:
                    current_url = page.url
                except Exception:
                    pass

                # Check if we've left the login page
                if not _is_login_url(current_url) and current_url != last_url:
                    # Check if logged in via cookies
                    if _is_logged_in(page):
                        print(
                            "[capture-auth-login] Login appears complete! Saving storage_state...",
                            file=sys.stderr,
                        )
                        break
                    # URL changed away from login but might not be logged in yet
                    # Wait a bit more
                    time.sleep(poll_interval * 2)
                    if _is_logged_in(page):
                        print(
                            "[capture-auth-login] Login appears complete! Saving storage_state...",
                            file=sys.stderr,
                        )
                        break

                last_url = current_url

                # Also check via DOM: if login form is gone, probably logged in
                if not _has_login_dom(page):
                    if _is_logged_in(page):
                        print(
                            "[capture-auth-login] Login form disappeared and session cookies found. Saving...",
                            file=sys.stderr,
                        )
                        break

            # Save storage state
            context.storage_state(path=str(output_path))
            elapsed = time.time() - start_time

            print(f"[capture-auth-login] SUCCESS: storage_state saved to {output_path}", file=sys.stderr)
            print("[capture-auth-login] Login successful! ✓", file=sys.stderr)

            result = {
                "status": "success",
                "url": page.url,
                "output_path": str(output_path),
                "elapsed_seconds": round(elapsed, 1),
            }
            print(json.dumps(result, ensure_ascii=False))
            return result

        except PlaywrightTimeout:
            result = {
                "status": "timeout",
                "url": page.url,
                "output_path": str(output_path),
            }
            print(json.dumps(result, ensure_ascii=False))
            return result
        finally:
            context.close()
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="capture-auth-login: Interactive login capture")
    parser.add_argument("--url", required=True, help="Target URL to navigate to")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save storage_state files (default: ~/.hermes/stats/)",
    )
    parser.add_argument(
        "--output-name",
        default=None,
        help="Custom output filename (default: derived from URL domain)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300,
        help="Max seconds to wait for login (default: 300)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.5,
        help="Seconds between login checks (default: 1.5)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else _default_stats_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.output_name:
        output_path = output_dir / args.output_name
    else:
        output_path = _default_output_path(args.url, output_dir)

    # Add .js extension if not present
    if not output_path.name.endswith(".js"):
        output_path = output_path.parent / f"{output_path.name}.js"

    run_auth_capture(
        url=args.url,
        output_path=output_path,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
