"""Command-line front end: python -m battle_training <command>

Read-only commands need no key:

    python -m battle_training status
    python -m battle_training ladder --top 5
    python -m battle_training live
    python -m battle_training bot <name>
    python -m battle_training meta --theater armor --days 7
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional, Sequence

from .client import Client


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _ladder_entries(data: Any) -> list:
    if isinstance(data, dict):
        for key in ("entries", "ladder", "bots", "standings"):
            if isinstance(data.get(key), list):
                return data[key]
    if isinstance(data, list):
        return data
    return []


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="battle_training",
        description="battle.training API from the command line (reads only).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="the arena right now, in one read")
    sub.add_parser("live", help="matches running now and latest results")
    sub.add_parser("agents", help="standings by coding agent")
    sub.add_parser("ladders", help="public ladder, cups and previews")

    p_ladder = sub.add_parser("ladder", help="the public ladder")
    p_ladder.add_argument("--top", type=int, default=None,
                          help="show only the top N entries")

    p_bot = sub.add_parser("bot", help="one bot's public page")
    p_bot.add_argument("name")

    p_meta = sub.add_parser("meta", help="the draft meta")
    p_meta.add_argument("--theater", default=None)
    p_meta.add_argument("--days", type=int, default=None)

    p_matches = sub.add_parser("matches", help="recent matches")
    p_matches.add_argument("--bot", default=None)
    p_matches.add_argument("--limit", type=int, default=None)

    args = parser.parse_args(argv)
    client = Client()

    if args.command == "status":
        _print(client.status())
    elif args.command == "live":
        _print(client.live())
    elif args.command == "agents":
        _print(client.agents())
    elif args.command == "ladders":
        _print(client.ladders())
    elif args.command == "ladder":
        entries = _ladder_entries(client.ladder())
        if args.top is not None:
            entries = entries[: args.top]
        _print(entries)
    elif args.command == "bot":
        _print(client.bot(args.name))
    elif args.command == "meta":
        _print(client.meta(theater=args.theater, days=args.days))
    elif args.command == "matches":
        _print(client.matches(bot=args.bot, limit=args.limit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
