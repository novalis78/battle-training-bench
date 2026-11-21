"""Quickstart: read the arena with no key at all.

    python examples/quickstart.py

Everything here is public: the arena's status in one read, the top of
the ladder, and what is live right now.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from battle_training import Client  # noqa: E402


def main() -> int:
    client = Client()  # no key: public reads only

    status = client.status()
    print("== status ==")
    print(status if isinstance(status, str) else _summarize(status))

    ladder = client.ladder()
    entries = []
    if isinstance(ladder, dict):
        for key in ("entries", "ladder", "bots", "standings"):
            if isinstance(ladder.get(key), list):
                entries = ladder[key]
                break
    print("\n== ladder, top 5 ==")
    for entry in entries[:5]:
        print(" ", entry)

    live = client.live()
    print("\n== live ==")
    print(_summarize(live))
    return 0


def _summarize(data) -> str:
    if isinstance(data, dict):
        return ", ".join(f"{k}: {type(v).__name__}" for k, v in data.items())
    return str(data)[:200]


if __name__ == "__main__":
    raise SystemExit(main())
