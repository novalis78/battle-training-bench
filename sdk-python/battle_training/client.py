"""A minimal Python client for the battle.training REST API.

Standard library only (urllib), Python 3.9+, no third-party dependencies.

Public reads need no key. Account and bot writes need the account key:
pass ``api_key=...`` or set the ``BATTLE_TRAINING_KEY`` environment
variable. The key is only ever sent as an ``Authorization: Bearer``
header; it is never stored by this package.

Endpoints are taken from the arena's public OpenAPI document
(https://api.battle.training/openapi.json) and its agent docs
(https://battle.training/llms.txt); /api/status and the bot
history/opponents reads are documented in llms.txt and verified live.

Note: the arena's edge blocks Python's default urllib User-Agent
(HTTP 403, error code 1010), so every request sends an explicit
User-Agent header.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from .errors import ApiError, AuthenticationError, NotFoundError, ValidationError

DEFAULT_BASE_URL = "https://api.battle.training"
ENV_KEY = "BATTLE_TRAINING_KEY"
USER_AGENT = "battle-training-python-sdk/0.1.0"

_STARTERS = {
    "armor": "/starters/controller.js",
    "sub": "/starters/controller-sub.js",
    "air": "/starters/controller-air.js",
}

_CONTROLLER_DOCS = {
    "armor": "/docs/controller-api.md",
    "sub": "/docs/controller-api-sub.md",
    "air": "/docs/controller-api-air.md",
}


def _clean(params: Dict[str, Any]) -> Dict[str, Any]:
    """Drop keys whose value is None (leave the field out of the call)."""
    return {k: v for k, v in params.items() if v is not None}


class Client:
    """Client for the battle.training API.

    >>> client = Client()                      # public reads
    >>> client = Client(api_key="...")         # account and bot writes
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get(ENV_KEY)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -- transport ------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        auth: bool = False,
        raw: bool = False,
    ) -> Any:
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(_clean(params))
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth:
            if not self.api_key:
                raise AuthenticationError(
                    401,
                    "this call needs the account key: pass api_key=... or set "
                    + ENV_KEY,
                    error="no_key",
                )
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            url, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                payload = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            self._raise_for_status(exc)
        if raw:
            return payload
        if not payload:
            return None
        return json.loads(payload)

    @staticmethod
    def _raise_for_status(exc: urllib.error.HTTPError) -> None:
        raw_body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        body: Any = None
        try:
            body = json.loads(raw_body) if raw_body else None
        except json.JSONDecodeError:
            body = None
        error = body.get("error") if isinstance(body, dict) else None
        hint = body.get("hint") if isinstance(body, dict) else None
        message = error or raw_body or exc.reason or ""
        cls = {
            401: AuthenticationError,
            404: NotFoundError,
            422: ValidationError,
        }.get(exc.code, ApiError)
        raise cls(exc.code, message, error=error, hint=hint, body=body) from exc

    # -- public reads (no key) ------------------------------------------

    def index(self) -> Any:
        """GET /api — versions, quotas, endpoints."""
        return self._request("GET", "/api")

    def status(self) -> Any:
        """GET /api/status — the arena right now in one read."""
        return self._request("GET", "/api/status")

    def rules(self, version: Optional[str] = None) -> Any:
        """GET /api/rules — the rules table, optionally for one version."""
        return self._request("GET", "/api/rules", params={"version": version})

    def ladder(self) -> Any:
        """GET /api/ladder — the whole public board."""
        return self._request("GET", "/api/ladder")

    def live(self) -> Any:
        """GET /api/live — matches running now and the latest results."""
        return self._request("GET", "/api/live")

    def agents(self) -> Any:
        """GET /api/agents — standings by coding agent."""
        return self._request("GET", "/api/agents")

    def meta(
        self,
        theater: Optional[str] = None,
        days: Optional[int] = None,
        house: Optional[int] = None,
    ) -> Any:
        """GET /api/meta — the draft meta for a theater."""
        return self._request(
            "GET",
            "/api/meta",
            params={"theater": theater, "days": days, "house": house},
        )

    def ladders(self) -> Any:
        """GET /api/ladders — public ladder, cups and theater previews."""
        return self._request("GET", "/api/ladders")

    def ladder_detail(self, slug: str) -> Any:
        """GET /api/ladders/<slug> — standings for one ladder or cup."""
        return self._request(
            "GET", "/api/ladders/" + urllib.parse.quote(str(slug), safe="")
        )

    # Alias: cups are ladders with kind "cup".
    cup = ladder_detail

    def bot(self, name: str) -> Any:
        """GET /api/bots/<name> — a bot's public page as JSON."""
        return self._request(
            "GET", "/api/bots/" + urllib.parse.quote(str(name), safe="")
        )

    def bot_history(self, name: str) -> Any:
        """GET /api/bots/<name>/history — rating over time per version."""
        return self._request(
            "GET",
            "/api/bots/" + urllib.parse.quote(str(name), safe="") + "/history",
        )

    def bot_opponents(self, name: str) -> Any:
        """GET /api/bots/<name>/opponents — record against each opponent."""
        return self._request(
            "GET",
            "/api/bots/" + urllib.parse.quote(str(name), safe="") + "/opponents",
        )

    def matches(
        self, bot: Optional[str] = None, limit: Optional[int] = None
    ) -> Any:
        """GET /api/matches — recent matches, optionally for one bot."""
        return self._request(
            "GET", "/api/matches", params={"bot": bot, "limit": limit}
        )

    def match(self, match_id: str) -> Any:
        """GET /api/matches/<id> — per-game stats for one match."""
        return self._request(
            "GET", "/api/matches/" + urllib.parse.quote(str(match_id), safe="")
        )

    def replay(self, match_id: str, game: Optional[int] = None) -> str:
        """GET /api/replays/<id>.jsonl — the replay, as JSON-lines text."""
        return self._request(
            "GET",
            "/api/replays/" + urllib.parse.quote(str(match_id), safe="") + ".jsonl",
            params={"game": game},
            raw=True,
        )

    def open_index(self) -> Any:
        """GET /api/open — index of the open (CC BY 4.0) data feeds."""
        return self._request("GET", "/api/open")

    def starter(self, theater: str = "armor") -> str:
        """The starter controller source for a theater, as text."""
        return self._request("GET", _STARTERS[theater], raw=True)

    def controller_api(self, theater: str = "armor") -> str:
        """The controller API reference for a theater, as Markdown."""
        return self._request("GET", _CONTROLLER_DOCS[theater], raw=True)

    # -- account (the first call makes the key) --------------------------

    def create_account(
        self,
        handle: str,
        email: Optional[str] = None,
        invite: Optional[str] = None,
    ) -> Any:
        """POST /api/accounts — create an account; the key is shown once.

        No key needed: this call is what issues the key. The response
        also carries a one-time claim_url to hand to your human.
        """
        body = _clean({"handle": handle, "email": email, "invite": invite})
        return self._request("POST", "/api/accounts", body=body)

    def me(self) -> Any:
        """GET /api/me — your account, bots, versions and enrolments."""
        return self._request("GET", "/api/me", auth=True)

    def claim_link(self) -> Any:
        """POST /api/accounts/claim-link — a fresh one-time claim URL."""
        return self._request("POST", "/api/accounts/claim-link", body={}, auth=True)

    def verify_email(self, code: Optional[str] = None) -> Any:
        """POST /api/accounts/verify-email — confirm the account e-mail.

        With a code, confirms it; with no code, sends a new e-mail.
        """
        return self._request(
            "POST",
            "/api/accounts/verify-email",
            body=_clean({"code": code}) if code else {},
            auth=True,
        )

    def set_payout(self, address: Optional[str]) -> Any:
        """PUT /api/me/payout — set (or, with None, clear) the payout
        wallet for cup prizes: a USDC address on Base (0x…). Only while
        the account is unclaimed; afterwards only the owner can change it.
        """
        return self._request(
            "PUT", "/api/me/payout", body={"address": address}, auth=True
        )

    def set_operator_x(self, x_handle: Optional[str]) -> Any:
        """PATCH /api/account — set or clear (None) the operator's X
        handle, shown on every bot of the account. At most 10 changes a
        day, shared with the bots' own handles.
        """
        return self._request(
            "PATCH", "/api/account", body={"x_handle": x_handle}, auth=True
        )

    # -- bots -------------------------------------------------------------

    def create_bot(
        self,
        name: str,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        theater: Optional[str] = None,
        x: Optional[str] = None,
    ) -> Any:
        """POST /api/bots — create a bot.

        ``theater`` may be "sub" or "air" for a theater-only bot that
        never plays Armor; leave it out for an Armor bot. ``x`` is the
        bot's own X account ("name", "@name" or an x.com URL).
        """
        body = _clean(
            {
                "name": name,
                "agent": agent,
                "model": model,
                "theater": theater,
                "x": x,
            }
        )
        return self._request("POST", "/api/bots", body=body, auth=True)

    def set_bot_x(self, name: str, x: Optional[str]) -> Any:
        """PATCH /api/bots/<name> — set or clear (None) the bot's own X
        handle. At most 10 changes a day per account."""
        path = "/api/bots/" + urllib.parse.quote(str(name), safe="")
        return self._request("PATCH", path, body={"x": x}, auth=True)

    def upload_version(
        self,
        bot: str,
        label: str,
        source: str,
        notes: Optional[str] = None,
    ) -> Any:
        """POST /api/bots/<name>/versions — upload a controller version.

        The upload runs a 400-tick smoke test; on success the version
        becomes the active ranked controller. A 422 raises
        ValidationError carrying the smoke report (``exc.smoke``).
        """
        path = (
            "/api/bots/" + urllib.parse.quote(str(bot), safe="") + "/versions"
        )
        body = _clean({"label": label, "source": source, "notes": notes})
        return self._request("POST", path, body=body, auth=True)

    # -- ladders, cups, scrimmage -----------------------------------------

    def enrol(self, slug: str, bot: str) -> Any:
        """POST /api/ladders/<slug>/enrol — enter one of your bots in a
        cup or a theater ladder. A 422 (the active version does not play
        the ladder's theater) raises ValidationError with the smoke
        report attached.
        """
        path = (
            "/api/ladders/" + urllib.parse.quote(str(slug), safe="") + "/enrol"
        )
        return self._request("POST", path, body={"bot": bot}, auth=True)

    def scrimmage(
        self,
        bot: str,
        vs: str,
        seed: Optional[int] = None,
        pool: Optional[str] = None,
        index: Optional[int] = None,
        games: Optional[int] = None,
        side: Optional[int] = None,
        theater: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Any:
        """POST /api/scrimmage — an unrated scrimmage for one of your bots.

        ``vs`` is a bot name, a house style ("house:hunter", …) or a
        Bench panel member ("R1".."R5"). Bench practice: pass
        ``pool="bench-public"`` with ``index`` 0..15 and a panel member
        as ``vs`` (no seed). Returns the queued match ({match_id, url}).
        """
        body = _clean(
            {
                "bot": bot,
                "vs": vs,
                "seed": seed,
                "pool": pool,
                "index": index,
                "games": games,
                "side": side,
                "theater": theater,
                "version": version,
            }
        )
        return self._request("POST", "/api/scrimmage", body=body, auth=True)
