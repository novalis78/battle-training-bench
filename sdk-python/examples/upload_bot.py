"""Upload a controller version for one of your bots.

Needs the account key (BATTLE_TRAINING_KEY or --api-key):

    export BATTLE_TRAINING_KEY=...          # shown once, at account creation
    python examples/upload_bot.py --bot my-bot --label v1 \
        --source controller.js [--ladder some-cup-slug]

The upload runs the arena's 400-tick smoke test. If the controller is
rejected, the script prints the smoke report and exits non-zero. With
--ladder, the bot is enrolled in that ladder or cup afterwards.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from battle_training import Client, ValidationError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bot", required=True, help="one of your bots")
    parser.add_argument("--label", required=True, help="version label, e.g. v1")
    parser.add_argument("--source", required=True,
                        help="path to the controller's JavaScript source")
    parser.add_argument("--ladder", default=None,
                        help="optional ladder/cup slug to enrol the bot in")
    parser.add_argument("--api-key", default=None,
                        help="account key (default: BATTLE_TRAINING_KEY)")
    args = parser.parse_args()

    with open(args.source, "r", encoding="utf-8") as fh:
        source = fh.read()

    client = Client(api_key=args.api_key)
    try:
        result = client.upload_version(args.bot, args.label, source)
    except ValidationError as exc:
        print(f"smoke test rejected the upload: {exc}", file=sys.stderr)
        if exc.smoke:
            print(f"smoke report: {exc.smoke}", file=sys.stderr)
        return 1
    print(f"uploaded and active: {result}")

    if args.ladder:
        print(f"enrolled: {client.enrol(args.ladder, args.bot)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
