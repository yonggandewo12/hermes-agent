import yaml
from pathlib import Path

from playwright_auth_models import (
    AuthSiteDefinition,
    AuthStep,
    AuthSuccessCriteria,
    PlaywrightAuthConfig,
)


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
