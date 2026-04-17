"""Tests for the startup allowlist warning check in gateway/run.py."""

import os
from unittest.mock import patch


def _would_warn():
    """Replicate the startup allowlist warning logic. Returns True if warning fires."""
    _any_allowlist = any(
        os.getenv(v)
        for v in ("TELEGRAM_ALLOWED_USERS", "DISCORD_ALLOWED_USERS",
                   "SLACK_ALLOWED_USERS",
                   "EMAIL_ALLOWED_USERS",
                   "MATTERMOST_ALLOWED_USERS",
                   "MATRIX_ALLOWED_USERS", "DINGTALK_ALLOWED_USERS", "FEISHU_ALLOWED_USERS", "WECOM_ALLOWED_USERS",
                   "GATEWAY_ALLOWED_USERS")
    )
    _allow_all = os.getenv("GATEWAY_ALLOW_ALL_USERS", "").lower() in ("true", "1", "yes") or any(
        os.getenv(v, "").lower() in ("true", "1", "yes")
        for v in ("TELEGRAM_ALLOW_ALL_USERS", "DISCORD_ALLOW_ALL_USERS",
                   "SLACK_ALLOW_ALL_USERS",
                   "EMAIL_ALLOW_ALL_USERS",
                   "MATTERMOST_ALLOW_ALL_USERS",
                   "MATRIX_ALLOWED_USERS", "DINGTALK_ALLOW_ALL_USERS", "FEISHU_ALLOW_ALL_USERS", "WECOM_ALLOW_ALL_USERS")
    )
    return not _any_allowlist and not _allow_all


class TestAllowlistStartupCheck:

    def test_removed_phone_platforms_are_not_advertised_in_cli_metadata(self):
        from pathlib import Path
        from hermes_cli import config as cli_config

        main_source = Path("hermes_cli/main.py").read_text(encoding="utf-8")

        assert 'Manage the messaging gateway (Telegram, Discord, WhatsApp)' not in main_source
        assert 'Delivery target: origin, local, telegram, discord, signal, or platform:chat_id' not in main_source
        assert "SIGNAL_ACCOUNT" not in cli_config._EXTRA_ENV_KEYS
        assert "SIGNAL_HTTP_URL" not in cli_config._EXTRA_ENV_KEYS
        assert "WHATSAPP_MODE" not in cli_config._EXTRA_ENV_KEYS
        assert "WHATSAPP_ENABLED" not in cli_config._EXTRA_ENV_KEYS

    def test_no_config_emits_warning(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _would_warn() is True

    def test_telegram_allow_all_users_suppresses_warning(self):
        with patch.dict(os.environ, {"TELEGRAM_ALLOW_ALL_USERS": "true"}, clear=True):
            assert _would_warn() is False

    def test_gateway_allow_all_users_suppresses_warning(self):
        with patch.dict(os.environ, {"GATEWAY_ALLOW_ALL_USERS": "yes"}, clear=True):
            assert _would_warn() is False
