"""Slack loading/thread metadata updates are not fresh human input after restart."""

from copy import deepcopy

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.slack.adapter import SlackAdapter


@pytest.mark.parametrize("previous_edit", [None, {"user": "U_TEST", "ts": "150.000001"}])
def test_metadata_update_is_ignored_with_empty_processed_cache(previous_edit):
    adapter = SlackAdapter(PlatformConfig(enabled=True))
    message = {"ts": "100.000001", "user": "U_TEST", "text": "original request"}
    if previous_edit:
        message["edited"] = previous_edit
    event = {"type": "message", "subtype": "message_changed", "channel": "C_TEST",
             "event_ts": "200.000001", "message": message, "previous_message": deepcopy(message)}
    event["message"]["reply_count"] = 2

    assert adapter._normalize_changed_message(event) is None


@pytest.mark.parametrize("previous_edit", [None, {"ts": "150.000001"}])
def test_new_human_edit_keeps_original_anchor_and_new_event_identity(previous_edit):
    adapter = SlackAdapter(PlatformConfig(enabled=True))
    event = {"type": "message", "subtype": "message_changed", "channel": "C_TEST",
             "event_ts": "200.000001", "previous_message": {"edited": previous_edit},
             "message": {"ts": "100.000001", "user": "U_TEST", "text": "<@U_BOT> new request",
                         "edited": {"ts": "200.000001"}}}

    normalized = adapter._normalize_changed_message(event)

    assert normalized["text"] == "<@U_BOT> new request"
    assert normalized["ts"] == "100.000001"
    assert normalized["_slack_changed_event_ts"] == "200.000001"
