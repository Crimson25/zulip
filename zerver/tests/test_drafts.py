import time
from typing import Any, Dict, List

import ujson

from zerver.lib.test_classes import ZulipTestCase
from zerver.models import Draft


class DraftCreationTests(ZulipTestCase):
    def create_and_check_drafts_for_success(self, draft_dicts: List[Dict[str, Any]],
                                            expected_draft_dicts: List[Dict[str, Any]]) -> None:
        hamlet = self.example_user("hamlet")

        # Make sure that there are no drafts in the database before
        # the test begins.
        self.assertEqual(Draft.objects.count(), 0)

        # Now send a POST request to the API endpoint.
        payload = {"drafts": ujson.dumps(draft_dicts)}
        resp = self.api_post(hamlet, "/api/v1/drafts", payload)
        self.assert_json_success(resp)

        # Finally check to make sure that the drafts were actually created properly.
        new_draft_dicts = [d.to_dict() for d in Draft.objects.order_by("last_edit_time")]
        self.assertEqual(new_draft_dicts, expected_draft_dicts)

    def create_and_check_drafts_for_error(self, draft_dicts: List[Dict[str, Any]],
                                          expected_message: str) -> None:
        hamlet = self.example_user("hamlet")

        # Make sure that there are no drafts in the database before
        # the test begins.
        self.assertEqual(Draft.objects.count(), 0)

        # Now send a POST request to the API endpoint.
        payload = {"drafts": ujson.dumps(draft_dicts)}
        resp = self.api_post(hamlet, "/api/v1/drafts", payload)
        self.assert_json_error(resp, expected_message)

        # Make sure that there are no drafts in the database at the
        # end of the test. Drafts should never be created in error
        # conditions.
        self.assertEqual(Draft.objects.count(), 0)

    def test_create_one_stream_draft_properly(self) -> None:
        hamlet = self.example_user("hamlet")
        visible_stream_name = self.get_streams(hamlet)[0]
        visible_stream_id = self.get_stream_id(visible_stream_name)
        draft_dicts = [{
            "type": "stream",
            "to": [visible_stream_id],
            "topic": "sync drafts",
            "content": "Let's add backend support for syncing drafts.",
            "timestamp": 1595479019.4391587,
        }]
        expected_draft_dicts = [{
            "type": "stream",
            "to": [visible_stream_id],
            "topic": "sync drafts",
            "content": "Let's add backend support for syncing drafts.",
            "timestamp": 1595479019.439159,  # We only go as far microseconds.
        }]
        self.create_and_check_drafts_for_success(draft_dicts, expected_draft_dicts)

    def test_create_one_personal_message_draft_properly(self) -> None:
        zoe = self.example_user("ZOE")
        draft_dicts = [{
            "type": "private",
            "to": [zoe.id],
            "topic": "This topic should be ignored.",
            "content": "What if we made it possible to sync drafts in Zulip?",
            "timestamp": 1595479019.43915,
        }]
        expected_draft_dicts = [{
            "type": "private",
            "to": [zoe.id],
            "topic": "",  # For private messages the topic should be ignored.
            "content": "What if we made it possible to sync drafts in Zulip?",
            "timestamp": 1595479019.43915,
        }]
        self.create_and_check_drafts_for_success(draft_dicts, expected_draft_dicts)

    def test_create_one_group_personal_message_draft_properly(self) -> None:
        zoe = self.example_user("ZOE")
        othello = self.example_user("othello")
        draft_dicts = [{
            "type": "private",
            "to": [zoe.id, othello.id],
            "topic": "This topic should be ignored.",
            "content": "What if we made it possible to sync drafts in Zulip?",
            "timestamp": 1595479019,
        }]
        expected_draft_dicts = [{
            "type": "private",
            "to": [zoe.id, othello.id],
            "topic": "",  # For private messages the topic should be ignored.
            "content": "What if we made it possible to sync drafts in Zulip?",
            "timestamp": 1595479019.0,
        }]
        self.create_and_check_drafts_for_success(draft_dicts, expected_draft_dicts)

    def test_create_batch_of_drafts_properly(self) -> None:
        hamlet = self.example_user("hamlet")
        visible_stream_name = self.get_streams(hamlet)[0]
        visible_stream_id = self.get_stream_id(visible_stream_name)
        zoe = self.example_user("ZOE")
        othello = self.example_user("othello")
        draft_dicts = [
            {
                "type": "stream",
                "to": [visible_stream_id],
                "topic": "sync drafts",
                "content": "Let's add backend support for syncing drafts.",
                "timestamp": 1595479019.43915,
            },  # Stream message draft
            {
                "type": "private",
                "to": [zoe.id],
                "topic": "This topic should be ignored.",
                "content": "What if we made it possible to sync drafts in Zulip?",
                "timestamp": 1595479020.43916,
            },  # Private message draft
            {
                "type": "private",
                "to": [zoe.id, othello.id],
                "topic": "",
                "content": "What if we made it possible to sync drafts in Zulip?",
                "timestamp": 1595479021.43916,
            },  # Private group message draft
        ]
        expected_draft_dicts = [
            {
                "type": "stream",
                "to": [visible_stream_id],
                "topic": "sync drafts",
                "content": "Let's add backend support for syncing drafts.",
                "timestamp": 1595479019.43915,
            },
            {
                "type": "private",
                "to": [zoe.id],
                "topic": "",
                "content": "What if we made it possible to sync drafts in Zulip?",
                "timestamp": 1595479020.43916,
            },
            {
                "type": "private",
                "to": [zoe.id, othello.id],
                "topic": "",
                "content": "What if we made it possible to sync drafts in Zulip?",
                "timestamp": 1595479021.43916,
            }
        ]
        self.create_and_check_drafts_for_success(draft_dicts, expected_draft_dicts)

    def test_missing_timestamps(self) -> None:
        """ If a timestamp is not provided for a draft dict then it should be automatically
        filled in. """
        hamlet = self.example_user("hamlet")
        visible_stream_name = self.get_streams(hamlet)[0]
        visible_stream_id = self.get_stream_id(visible_stream_name)

        draft_dicts = [{
            "type": "stream",
            "to": [visible_stream_id],
            "topic": "sync drafts",
            "content": "Let's add backend support for syncing drafts.",
        }]

        self.assertEqual(Draft.objects.count(), 0)

        current_time = round(time.time(), 6)
        payload = {"drafts": ujson.dumps(draft_dicts)}
        resp = self.api_post(hamlet, "/api/v1/drafts", payload)
        self.assert_json_success(resp)

        new_drafts = Draft.objects.all()
        self.assertEqual(Draft.objects.count(), 1)
        new_draft = new_drafts[0].to_dict()
        self.assertTrue(isinstance(new_draft["timestamp"], float))
        # Since it would be too tricky to get the same times, perform
        # a relative check.
        self.assertTrue(new_draft["timestamp"] > current_time)

    def test_invalid_timestamp(self) -> None:
        draft_dicts = [{
            "type": "stream",
            "to": [],
            "topic": "sync drafts",
            "content": "Let's add backend support for syncing drafts.",
            "timestamp": -10.10,
        }]
        self.create_and_check_drafts_for_error(
            draft_dicts,
            "Timestamp must not be negative."
        )

    def test_create_non_stream_draft_with_no_recipient(self) -> None:
        """ When "to" is an empty list, the type should become "" as well. """
        draft_dicts = [
            {
                "type": "private",
                "to": [],
                "topic": "sync drafts",
                "content": "Let's add backend support for syncing drafts.",
                "timestamp": 1595479019.43915,
            },
            {
                "type": "",
                "to": [],
                "topic": "sync drafts",
                "content": "Let's add backend support for syncing drafts.",
                "timestamp": 1595479019.43915,
            },
        ]
        expected_draft_dicts = [
            {
                "type": "",
                "to": [],
                "topic": "",
                "content": "Let's add backend support for syncing drafts.",
                "timestamp": 1595479019.43915,
            },
            {
                "type": "",
                "to": [],
                "topic": "",
                "content": "Let's add backend support for syncing drafts.",
                "timestamp": 1595479019.43915,
            },
        ]
        self.create_and_check_drafts_for_success(draft_dicts, expected_draft_dicts)

    def test_create_stream_draft_with_no_recipient(self) -> None:
        draft_dicts = [{
            "type": "stream",
            "to": [],
            "topic": "sync drafts",
            "content": "Let's add backend support for syncing drafts.",
            "timestamp": 1595479019.439159,
        }]
        self.create_and_check_drafts_for_error(
            draft_dicts,
            "Must specify exactly 1 stream ID for stream messages"
        )

    def test_create_stream_draft_for_inaccessible_stream(self) -> None:
        # When the user does not have permission to access the stream:
        stream = self.make_stream("Secret Society", invite_only=True)
        draft_dicts = [{
            "type": "stream",
            "to": [stream.id],  # This can't be accessed by hamlet.
            "topic": "sync drafts",
            "content": "Let's add backend support for syncing drafts.",
            "timestamp": 1595479019.43915,
        }]
        self.create_and_check_drafts_for_error(draft_dicts, "Invalid stream id")

        # When the stream itself does not exist:
        draft_dicts = [{
            "type": "stream",
            "to": [99999999999999],  # Hopefully, this doesn't exist.
            "topic": "sync drafts",
            "content": "Let's add backend support for syncing drafts.",
            "timestamp": 1595479019.43915,
        }]
        self.create_and_check_drafts_for_error(draft_dicts, "Invalid stream id")

    def test_create_personal_message_draft_for_non_existing_user(self) -> None:
        draft_dicts = [{
            "type": "private",
            "to": [99999999999999],  # Hopefully, this doesn't exist either.
            "topic": "This topic should be ignored.",
            "content": "What if we made it possible to sync drafts in Zulip?",
            "timestamp": 1595479019.43915,
        }]
        self.create_and_check_drafts_for_error(draft_dicts, "Invalid user ID 99999999999999")

    def test_create_draft_with_null_bytes(self) -> None:
        draft_dicts = [{
            "type": "",
            "to": [],
            "topic": "sync drafts.",
            "content": "Some regular \x00 content here",
            "timestamp": 1595479019.439159,
        }]
        self.create_and_check_drafts_for_error(
            draft_dicts,
            "Content must not contain null bytes"
        )

        draft_dicts = [{
            "type": "stream",
            "to": [10],
            "topic": "thinking about \x00",
            "content": "Let's add backend support for syncing drafts.",
            "timestamp": 1595479019.439159,
        }]
        self.create_and_check_drafts_for_error(
            draft_dicts,
            "Topic must not contain null bytes"
        )