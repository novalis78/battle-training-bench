"""Tests for the battle.training client.

Two layers:

- Mocked tests: urllib's urlopen is replaced, so every write path is
  checked for its exact method, URL, headers and JSON payload, and the
  error mapping (401/404/422, plus a plain 409) is exercised. No network.
- Live tests: the real public endpoints, no key, reads only, no side
  effects. They skip themselves when the network is unreachable.

Run:  python -m unittest discover -s tests -v     (from sdk-python/)
"""

import io
import json
import os
import sys
import unittest
import urllib.error
import urllib.request
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from battle_training import (  # noqa: E402
    ApiError,
    AuthenticationError,
    Client,
    NotFoundError,
    ValidationError,
)

BASE = "https://api.battle.training"
KEY = "test-key-123"


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        if isinstance(payload, (bytes, str)):
            self._data = payload.encode() if isinstance(payload, str) else payload
        else:
            self._data = json.dumps(payload).encode()

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class MockedCase(unittest.TestCase):
    """Patches urlopen; records the last request it received."""

    def setUp(self):
        self.requests = []
        self.next_payload = {"ok": True}
        self.next_status = 200

        def fake_urlopen(request, timeout=None):
            self.requests.append(request)
            if self.next_status >= 400:
                body = json.dumps(self.next_payload).encode()
                raise urllib.error.HTTPError(
                    request.full_url, self.next_status, "error",
                    hdrs=None, fp=io.BytesIO(body),
                )
            return FakeResponse(self.next_payload, self.next_status)

        patcher = mock.patch.object(urllib.request, "urlopen", fake_urlopen)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = Client(api_key=KEY)

    @property
    def last(self):
        return self.requests[-1]

    def last_json(self):
        return json.loads(self.last.data.decode("utf-8"))


class WritePathTests(MockedCase):
    def test_create_account_posts_handle_and_email_without_auth(self):
        self.client.create_account("my-agent", email="human@example.com")
        self.assertEqual(self.last.get_method(), "POST")
        self.assertEqual(self.last.full_url, BASE + "/api/accounts")
        self.assertEqual(
            self.last_json(), {"handle": "my-agent", "email": "human@example.com"}
        )
        self.assertIsNone(self.last.get_header("Authorization"))

    def test_create_account_omits_optional_fields(self):
        self.client.create_account("my-agent")
        self.assertEqual(self.last_json(), {"handle": "my-agent"})

    def test_me_sends_bearer_key(self):
        self.client.me()
        self.assertEqual(self.last.get_method(), "GET")
        self.assertEqual(self.last.full_url, BASE + "/api/me")
        self.assertEqual(self.last.get_header("Authorization"), f"Bearer {KEY}")

    def test_claim_link_posts_with_auth(self):
        self.client.claim_link()
        self.assertEqual(self.last.get_method(), "POST")
        self.assertEqual(self.last.full_url, BASE + "/api/accounts/claim-link")
        self.assertEqual(self.last.get_header("Authorization"), f"Bearer {KEY}")

    def test_verify_email_posts_code(self):
        self.client.verify_email("123456")
        self.assertEqual(self.last.get_method(), "POST")
        self.assertEqual(self.last.full_url, BASE + "/api/accounts/verify-email")
        self.assertEqual(self.last_json(), {"code": "123456"})

    def test_create_bot_full_payload(self):
        self.client.create_bot(
            "falcon", agent="claude-code", model="opus", theater="sub", x="@falcon"
        )
        self.assertEqual(self.last.get_method(), "POST")
        self.assertEqual(self.last.full_url, BASE + "/api/bots")
        self.assertEqual(
            self.last_json(),
            {
                "name": "falcon",
                "agent": "claude-code",
                "model": "opus",
                "theater": "sub",
                "x": "@falcon",
            },
        )
        self.assertEqual(self.last.get_header("Content-type"), "application/json")

    def test_create_bot_minimal_payload(self):
        self.client.create_bot("falcon")
        self.assertEqual(self.last_json(), {"name": "falcon"})

    def test_upload_version_payload(self):
        self.client.upload_version("falcon", "v1", "function tick() {}")
        self.assertEqual(self.last.get_method(), "POST")
        self.assertEqual(self.last.full_url, BASE + "/api/bots/falcon/versions")
        self.assertEqual(
            self.last_json(), {"label": "v1", "source": "function tick() {}"}
        )

    def test_set_payout_puts_address(self):
        address = "0x" + "ab" * 20
        self.client.set_payout(address)
        self.assertEqual(self.last.get_method(), "PUT")
        self.assertEqual(self.last.full_url, BASE + "/api/me/payout")
        self.assertEqual(self.last_json(), {"address": address})

    def test_set_payout_clear_sends_null(self):
        self.client.set_payout(None)
        self.assertEqual(self.last_json(), {"address": None})

    def test_enrol_posts_bot(self):
        self.client.enrol("november-cup", "falcon")
        self.assertEqual(self.last.get_method(), "POST")
        self.assertEqual(self.last.full_url, BASE + "/api/ladders/november-cup/enrol")
        self.assertEqual(self.last_json(), {"bot": "falcon"})

    def test_scrimmage_posts_seed_match(self):
        self.client.scrimmage("falcon", "house:hunter", seed=12345)
        self.assertEqual(self.last.get_method(), "POST")
        self.assertEqual(self.last.full_url, BASE + "/api/scrimmage")
        self.assertEqual(
            self.last_json(),
            {"bot": "falcon", "vs": "house:hunter", "seed": 12345},
        )

    def test_scrimmage_bench_pool_payload(self):
        self.client.scrimmage("falcon", "R3", pool="bench-public", index=7)
        self.assertEqual(
            self.last_json(),
            {"bot": "falcon", "vs": "R3", "pool": "bench-public", "index": 7},
        )

    def test_set_bot_x_patch_payload(self):
        self.client.set_bot_x("falcon", "@falcon")
        self.assertEqual(self.last.get_method(), "PATCH")
        self.assertEqual(self.last.full_url, BASE + "/api/bots/falcon")
        self.assertEqual(self.last_json(), {"x": "@falcon"})

    def test_set_bot_x_clear_sends_null(self):
        self.client.set_bot_x("falcon", None)
        self.assertEqual(self.last_json(), {"x": None})

    def test_set_operator_x_patch_payload(self):
        self.client.set_operator_x("@operator")
        self.assertEqual(self.last.get_method(), "PATCH")
        self.assertEqual(self.last.full_url, BASE + "/api/account")
        self.assertEqual(self.last_json(), {"x_handle": "@operator"})


class ErrorMappingTests(MockedCase):
    def test_401_raises_authentication_error(self):
        self.next_status = 401
        self.next_payload = {"error": "unauthorized"}
        with self.assertRaises(AuthenticationError) as ctx:
            self.client.me()
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(ctx.exception.error, "unauthorized")

    def test_404_raises_not_found(self):
        self.next_status = 404
        self.next_payload = {"error": "no_such_bot"}
        with self.assertRaises(NotFoundError):
            self.client.bot("nope")

    def test_422_upload_raises_validation_error_with_smoke(self):
        smoke = {"stage": "smoke", "ticks": 400, "failed": "timeout",
                 "failures": 3, "hint": "tick() never returns"}
        self.next_status = 422
        self.next_payload = {"error": "smoke_failed", "smoke": smoke}
        with self.assertRaises(ValidationError) as ctx:
            self.client.upload_version("falcon", "v1", "broken")
        self.assertEqual(ctx.exception.smoke, smoke)
        self.assertEqual(ctx.exception.report, smoke)

    def test_409_raises_plain_api_error(self):
        self.next_status = 409
        self.next_payload = {"error": "name_taken"}
        with self.assertRaises(ApiError) as ctx:
            self.client.create_bot("falcon")
        self.assertNotIsInstance(ctx.exception, ValidationError)
        self.assertEqual(ctx.exception.error, "name_taken")

    def test_write_without_key_raises_before_http(self):
        keyless = Client()
        with mock.patch.dict(os.environ, {}, clear=True):
            keyless = Client()
            with self.assertRaises(AuthenticationError):
                keyless.create_bot("falcon")
        self.assertEqual(self.requests, [])


class ReadPathTests(MockedCase):
    def test_key_read_from_environment(self):
        with mock.patch.dict(os.environ, {"BATTLE_TRAINING_KEY": "env-key"}):
            client = Client()
            client.me()
        self.assertEqual(self.last.get_header("Authorization"), "Bearer env-key")

    def test_meta_query_params(self):
        self.client.meta(theater="armor", days=7)
        self.assertEqual(
            self.last.full_url, BASE + "/api/meta?theater=armor&days=7"
        )

    def test_matches_query_params(self):
        self.client.matches(bot="falcon", limit=50)
        self.assertEqual(
            self.last.full_url, BASE + "/api/matches?bot=falcon&limit=50"
        )

    def test_bot_name_is_url_encoded(self):
        self.client.bot("my bot")
        self.assertEqual(self.last.full_url, BASE + "/api/bots/my%20bot")

    def test_rules_version_param(self):
        self.client.rules(version="sub-s1.0.0")
        self.assertEqual(
            self.last.full_url, BASE + "/api/rules?version=sub-s1.0.0"
        )

    def test_replay_returns_text_and_game_param(self):
        self.next_payload = '{"tick": 1}\n{"tick": 2}\n'
        text = self.client.replay("m-123", game=1)
        self.assertEqual(text, '{"tick": 1}\n{"tick": 2}\n')
        self.assertEqual(
            self.last.full_url, BASE + "/api/replays/m-123.jsonl?game=1"
        )


def _live_client_or_skip(testcase):
    client = Client(timeout=15)
    try:
        client.status()
    except Exception as exc:  # network down or edge blocked: skip, don't fail
        testcase.skipTest(f"live API unreachable: {exc}")
    return client


class LiveTests(unittest.TestCase):
    """Real public endpoints, no key, reads only."""

    def setUp(self):
        self.client = _live_client_or_skip(self)

    def test_live_status(self):
        self.assertIsInstance(self.client.status(), dict)

    def test_live_ladder(self):
        self.assertIsInstance(self.client.ladder(), dict)

    def test_live_rules(self):
        self.assertIsInstance(self.client.rules(), dict)

    def test_live_bot_page_history_and_opponents(self):
        ladder = self.client.ladder()
        name = None
        if isinstance(ladder, dict):
            for key in ("entries", "ladder", "bots", "standings"):
                rows = ladder.get(key)
                if isinstance(rows, list) and rows:
                    name = rows[0].get("bot") or rows[0].get("name")
                    break
        if not name:
            self.skipTest("no bot name found on the live ladder")
        self.assertIsInstance(self.client.bot(name), dict)
        self.assertIsInstance(self.client.bot_history(name), (dict, list))
        self.assertIsInstance(self.client.bot_opponents(name), (dict, list))


if __name__ == "__main__":
    unittest.main()
