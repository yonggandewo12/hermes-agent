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
