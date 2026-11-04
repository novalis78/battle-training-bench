// The open ladder at the moment an edition is scored: a copy of the public GET /api/benchmark (the same object
// rc1's results/v1.0-rc1/open-ladder-snapshot.json holds), written where score.py and figures.py read it.
//
//   node research/bench/snapshot-ladder.mjs --edition v1.1 [--api https://api.battle.training]
//
// Public data only (no key). Writes research/bench/results/<edition>/open-ladder-snapshot.json and prints its
// season, totals and generated_at; refuses to overwrite an existing snapshot unless --force.
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => { if (a.startsWith("--")) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith("--") ? all[i + 1] : "1"]); return acc; }, []));
const edition = args.edition;
if (!edition) { console.error("usage: snapshot-ladder.mjs --edition <id> [--api URL] [--force]"); process.exit(1); }
const api = (args.api ?? "https://api.battle.training").replace(/\/$/, "");
const out = join(dirname(new URL(import.meta.url).pathname), "results", edition, "open-ladder-snapshot.json");
if (existsSync(out) && !args.force) { console.error(`${out} exists; pass --force to replace it`); process.exit(1); }

const r = await fetch(`${api}/api/benchmark`, { headers: { accept: "application/json", "user-agent": "bt-bench-snapshot" } });
if (!r.ok) { console.error(`GET /api/benchmark: ${r.status}`); process.exit(1); }
const d = await r.json();
for (const k of ["season", "bots", "totals", "generated_at"]) if (!(k in d)) { console.error(`unexpected answer: no ${k}`); process.exit(1); }
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({ ...d, snapshot: { edition, source: `${api}/api/benchmark`, taken_at: Date.now() } }, null, 1));
console.log(`${out}: season ${d.season.id} (started ${new Date(d.season.started_at).toISOString()}), ${d.totals.sets} sets, ${d.bots.length} bots, generated ${new Date(d.generated_at).toISOString()}`);
