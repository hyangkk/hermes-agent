"""Slack status starts and clears with the selected API's payload contract."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.slack import adapter as slack


@pytest.mark.asyncio
async def test_native_typing_lifecycle_starts_processing_and_returns_to_active():
    client = SimpleNamespace(
        agents_sessions_setStatus=AsyncMock(), assistant_threads_setStatus=AsyncMock()
    )
    adapter = slack.SlackAdapter(PlatformConfig(enabled=True))
    adapter._app = SimpleNamespace(client=client)
    adapter._get_client = lambda *args, **kwargs: client
    metadata = {"thread_id": "123.456", "team_id": "T_TEST"}

    with patch.object(slack, "_AGENT_SESSIONS_SUPPORTED", True):
        adapter.set_status_text("C_TEST", "요청을 확인하고 있어요…")
        await adapter.send_typing("C_TEST", metadata=metadata)
        assert adapter._active_status_threads
        await adapter.stop_typing("C_TEST", metadata=metadata)

    assert [c.kwargs for c in client.agents_sessions_setStatus.await_args_list] == [
        {"channel_id": "C_TEST", "thread_ts": "123.456", "status": "processing"},
        {"channel_id": "C_TEST", "thread_ts": "123.456", "status": "active"},
    ]
    assert not adapter._active_status_threads
    client.assistant_threads_setStatus.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("sdk_supports_sessions", [False, True])
async def test_legacy_fallback_keeps_text_and_empty_clear(sdk_supports_sessions):
    client = SimpleNamespace(
        agents_sessions_setStatus=None, assistant_threads_setStatus=AsyncMock()
    )
    adapter = slack.SlackAdapter.__new__(slack.SlackAdapter)
    adapter._get_client = lambda *args, **kwargs: client

    with patch.object(slack, "_AGENT_SESSIONS_SUPPORTED", sdk_supports_sessions):
        for status in ("작업을 준비하고 있어요…", ""):
            await adapter._set_thread_status("C_TEST", "T_TEST", "123.456", status, "failed")

    assert [c.kwargs["status"] for c in client.assistant_threads_setStatus.await_args_list] == [
        "작업을 준비하고 있어요…", ""
    ]
