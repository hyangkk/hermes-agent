"""Slack Bolt must keep the authenticated client without duplicate-token warnings."""

import logging
from unittest.mock import AsyncMock, call

import pytest

from slack_bolt.async_app import AsyncApp

from gateway.config import PlatformConfig
from plugins.platforms.slack import adapter as slack_adapter


@pytest.mark.asyncio
@pytest.mark.parametrize("proxy_url", [None, "http://proxy.example.com:3128"])
async def test_connect_preserves_authenticated_client_without_duplicate_token_warning(
    monkeypatch, caplog, proxy_url
):
    adapter = slack_adapter.SlackAdapter(
        PlatformConfig(enabled=True, token="xoxb-primary,xoxb-secondary")
    )
    authenticate = AsyncMock()

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-environment-fallback")
    monkeypatch.setattr(slack_adapter, "_resolve_slack_proxy_url", lambda: proxy_url)
    monkeypatch.setattr(
        slack_adapter, "_get_scoped_secret", lambda name, default="": "xapp-test"
    )
    monkeypatch.setattr(adapter, "_acquire_platform_lock", lambda *args: True)
    monkeypatch.setattr(adapter, "_authenticate_workspace", authenticate)
    monkeypatch.setattr(adapter, "_register_bolt_handlers", lambda: None)
    monkeypatch.setattr(adapter, "_start_socket_mode_handler", lambda: None)
    monkeypatch.setattr(adapter, "_ensure_socket_watchdog", lambda: None)

    with caplog.at_level(logging.WARNING, logger="slack_bolt.AsyncApp"):
        connected = await adapter.connect()

    assert connected is True
    assert isinstance(adapter._app, AsyncApp)
    assert adapter._app.client.token == "xoxb-primary"
    assert adapter._app.client.proxy == proxy_url
    assert slack_adapter._HERMES_SLACK_USER_AGENT_PREFIX in adapter._app.client.headers["User-Agent"]
    assert authenticate.await_args_list == [
        call("xoxb-primary", proxy_url),
        call("xoxb-secondary", proxy_url),
    ]
    assert not any("will be unused" in record.getMessage() for record in caplog.records)
