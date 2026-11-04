#!/usr/bin/env python3
"""Draft compositions and announced plans (`say`) per entrant, from public ladder replays (the first 300 KB of each,
enough for the header with the drafts and the opening `say` lines). Edition v1.1 field, top entrants by Bench score.
  python3 research/paper/drafts_v11.py  ->  research/bench/results/v1.1/drafts.json"""
import os, json, csv, collections, urllib.request, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = f"{ROOT}/research/bench/results/v1.1"; B = "https://api.battle.training"
rows = list(csv.DictReader(open(f"{RES}/scores.csv")))
bots = [r["bot"] for r in sorted(rows, key=lambda r: -float(r["bench"])) if r["house"] == "0" and not r["panel"] and not r["bot"].startswith("pilot-")][:30]
def get(u, limit=None):
    with urllib.request.urlopen(u, timeout=40) as r: return (r.read(limit) if limit else r.read()).decode(errors="ignore")
out = {}
for b in bots:
    try: ms = json.loads(get(f"{B}/api/matches?bot={b}&limit=8")); ms = ms.get("matches", ms)
    except Exception as e: print(b, "matches failed", e); continue
    drafts = collections.Counter(); says = collections.Counter(); n = 0
    for m in ms[:6]:
        for g in (1, 2):
            try: txt = get(f"{B}/api/replays/{m['id']}.jsonl?game={g}", 300_000)
            except Exception: continue
            lines = txt.split("\n")
            try: h = json.loads(lines[0])
            except Exception: continue
            side = next((i for i, x in enumerate(h.get("bots", [])) if x["name"] == b), None)
            if side is None or not h.get("drafts"): continue
            drafts["+".join(sorted(h["drafts"][side]))] += 1; n += 1
            for l in lines[1:400]:
                if '"s":' in l:
                    try: t = json.loads(l); o = t["o"][side]
                    except Exception: continue
                    if isinstance(o, dict) and o.get("s"): says[o["s"][:70]] += 1
    out[b] = {"games": n, "drafts": drafts.most_common(3), "says": [s for s, _ in says.most_common(2)]}
    print(b, n, drafts.most_common(2), "|", out[b]["says"][:1])
json.dump({"source": "public ladder replays (GET /api/replays, first 300 KB), last 6 sets per bot, top 30 entrants by Bench v1.1 score", "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "bots": out}, open(f"{RES}/drafts.json", "w"), indent=1)
print("written", f"{RES}/drafts.json")
