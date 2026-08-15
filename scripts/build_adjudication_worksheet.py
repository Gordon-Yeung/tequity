#!/usr/bin/env python3
"""
Build a portable side-by-side worksheet for a two-coder calibration session.

The Compare & Adjudicate screen already shows this, but it needs the app running
and it can't be marked up, printed, or attached to a methods appendix. This
writes the same comparison to Markdown (walk through it with the other coder)
and CSV (the record of what was decided).

Two things it does that the Compare screen does not:

1. COVERAGE AUDIT. `progress.last_turn_viewed` is not trustworthy -- on obsid
   2204 coder 1 records 67 while holding a flag at turn 227. So coverage is
   inferred as max(last flagged turn, last_turn_viewed) and reported against the
   real end of the transcript. If a coding stops well short of the end, an
   "only coder X flagged this" row is not disagreement, it is absence of data,
   and the script says so instead of letting the stats imply otherwise.

2. THRESHOLD DIAGNOSTIC. When one coder's flags are almost a subset of the
   other's, the pair disagrees about *how much evidence is enough*, not about
   what the categories mean. Those two problems have different fixes, and the
   category-level stats alone don't separate them.

Reuses tools/coder/app.py and tools/coder/irr.py so this can never drift from
what the app reports.

Usage:
    py -3 scripts/build_adjudication_worksheet.py --obsid 2204
    py -3 scripts/build_adjudication_worksheet.py --obsid 2204 --coders 1 2 --llm
    py -3 scripts/build_adjudication_worksheet.py --obsid 2204 --scope full
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools" / "coder"))

import app as coder  # noqa: E402
import irr  # noqa: E402

OUT_DIR = REPO_ROOT / "data" / "adjudication"

# Canonical labels, mirrored from the coder app's codebook (tools/coder/static/
# index.html). Kept here so the HTML board is self-describing without the app.
CATEGORY_LABELS = {
    "A": "Fixed-Ability Framing",
    "B": "Deficit Labeling / Grouping",
    "C": "Problem in Student / Home / Background",
    "D": "Deficit Attribution (Behavior/Motivation)",
    "E": "Lowered Expectations",
    "F": "Comparative Deficit",
    "G": "Totalizing Negation",
    "Other": "Other (specify)",
}


def load_coding(obsid, coder_id):
    data = coder.read_json(coder.coder_path(obsid, coder_id))
    if data is None:
        raise SystemExit(
            f"No coding at {coder.coder_path(obsid, coder_id).relative_to(REPO_ROOT)}"
        )
    return data


def attested_through(coding):
    """Furthest turn we have evidence this coder actually reached.

    Takes the max of the progress marker and the last flag rather than trusting
    the marker, which lags whenever a coder jumps ahead or the autosave for the
    final scroll never landed.
    """
    turns = [s["turn"] for s in coding.get("scenes", [])]
    return max([coding.get("progress", {}).get("last_turn_viewed") or 0] + turns)


def teacher_turns(turns):
    return [t["turn_num"] for t in turns if coder.is_teacher(t["speaker"])]


def status_for(turn, flags_by_coder, cats_by_coder, coder_ids):
    """AGREE / CATEGORY-DIFF / ONLY-<id> for one turn."""
    who = [c for c in coder_ids if turn in flags_by_coder[c]]
    if len(who) < len(coder_ids):
        return "ONLY-" + "+".join(who)
    cats = [frozenset(cats_by_coder[c].get(turn, set())) for c in coder_ids]
    return "AGREE" if len(set(cats)) == 1 else "CATEGORY-DIFF"


def fmt(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def build_html(payload, out_dir, stem):
    """Write a self-contained, offline interactive adjudication board.

    One card per disputed turn: the quote in context, all coders side by side,
    and a decision panel. Decisions live in the browser's localStorage (no
    server), and Export writes a decisions CSV/JSON that lines up with the
    worksheet CSV's decision columns. Nothing external is loaded, so the file
    works from a flash drive or an email attachment.
    """
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    html = _HTML_TEMPLATE.replace("/*__DATA__*/", data_json)
    html_path = out_dir / f"{stem}_board.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


# Kept as one string so the board is a single portable file. Data is injected at
# the /*__DATA__*/ token; everything else is static.
_HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Adjudication board</title>
<style>
  :root {
    --bg:#f6f7f9; --panel:#fff; --ink:#1c2024; --muted:#6b7280; --line:#e3e6ea;
    --accent:#2563eb; --agree:#0e9f6e; --only:#d97706; --catdiff:#7c3aed;
    --mark:#fff3bf; --markink:#5c4813; --chip:#eef1f5; --ok:#0e9f6e;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg:#14171a; --panel:#1c2024; --ink:#e6e9ec; --muted:#9aa3ad; --line:#2b3138;
      --accent:#6ea8fe; --agree:#3ddc97; --only:#f0b463; --catdiff:#c4a7f7;
      --mark:#4a3f12; --markink:#ffe9a8; --chip:#262b31; --ok:#3ddc97;
    }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  header { position:sticky; top:0; z-index:5; background:var(--panel);
    border-bottom:1px solid var(--line); padding:14px 20px; }
  h1 { font-size:18px; margin:0 0 2px; }
  .sub { color:var(--muted); font-size:13px; }
  .stats { display:flex; flex-wrap:wrap; gap:14px; margin-top:10px; font-size:13px; }
  .stat { background:var(--chip); border-radius:8px; padding:6px 10px; }
  .stat b { font-size:15px; }
  .banner { background:color-mix(in srgb, var(--only) 16%, transparent);
    border:1px solid color-mix(in srgb, var(--only) 45%, transparent);
    color:var(--ink); border-radius:8px; padding:10px 12px; margin-top:10px; font-size:13px; }
  .toolbar { display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin-top:12px; }
  .toolbar select, .toolbar button { font:inherit; padding:6px 10px; border-radius:8px;
    border:1px solid var(--line); background:var(--panel); color:var(--ink); cursor:pointer; }
  .toolbar button:hover { border-color:var(--accent); }
  .toolbar .grow { flex:1; }
  .progress { font-size:13px; color:var(--muted); }
  .progress b { color:var(--ink); }
  main { max-width:1080px; margin:0 auto; padding:20px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:12px;
    padding:16px 18px; margin-bottom:16px; scroll-margin-top:180px; }
  .card.resolved { border-color:color-mix(in srgb, var(--ok) 55%, var(--line)); }
  .card-head { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
  .turn-no { font-size:16px; font-weight:700; }
  .badge { font-size:11px; font-weight:700; letter-spacing:.03em; text-transform:uppercase;
    padding:3px 8px; border-radius:999px; color:#fff; }
  .badge.AGREE { background:var(--agree); }
  .badge.CATEGORY-DIFF { background:var(--catdiff); }
  .badge.ONLY { background:var(--only); }
  .resolved-tag { margin-left:auto; font-size:12px; color:var(--ok); font-weight:600; display:none; }
  .card.resolved .resolved-tag { display:inline; }
  .context { border-left:3px solid var(--line); padding:2px 0 2px 12px; margin:0 0 12px;
    font-size:13.5px; color:var(--muted); }
  .context .row { margin:3px 0; }
  .context .row.target { color:var(--ink); }
  .context .spk { font-weight:600; text-transform:capitalize; }
  .context .target .spk { color:var(--accent); }
  mark { background:var(--mark); color:var(--markink); padding:0 2px; border-radius:3px; }
  .coders { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px;
    margin-bottom:14px; }
  .coder { border:1px solid var(--line); border-radius:10px; padding:10px 12px; font-size:13px; }
  .coder h4 { margin:0 0 6px; font-size:13px; display:flex; align-items:center; gap:6px; }
  .dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
  .dot.on { background:var(--only); } .dot.off { background:var(--line); }
  .coder.flagged { border-color:color-mix(in srgb, var(--only) 45%, var(--line)); }
  .cats { display:flex; flex-wrap:wrap; gap:4px; margin:4px 0; }
  .cat { font-size:11px; font-weight:700; background:var(--chip); border-radius:6px; padding:2px 6px; }
  .conf { color:var(--muted); font-size:12px; }
  .note { margin-top:5px; font-style:italic; color:var(--muted); }
  .span { margin-top:5px; } .span q { background:var(--mark); color:var(--markink);
    padding:1px 4px; border-radius:3px; font-style:normal; }
  .decision { border-top:1px dashed var(--line); padding-top:12px; }
  .decision .lbl { font-size:12px; text-transform:uppercase; letter-spacing:.04em;
    color:var(--muted); margin:0 0 6px; }
  .catpick { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px; }
  .catpick label { display:inline-flex; align-items:center; gap:5px; font-size:13px;
    border:1px solid var(--line); border-radius:8px; padding:4px 9px; cursor:pointer; }
  .catpick label:hover { border-color:var(--accent); }
  .catpick input { accent-color:var(--accent); }
  .incl { display:flex; gap:14px; margin-bottom:10px; font-size:13px; }
  .incl label { display:inline-flex; gap:5px; align-items:center; cursor:pointer; }
  .decision textarea, .decision input.rule { width:100%; font:inherit; padding:7px 9px;
    border:1px solid var(--line); border-radius:8px; background:var(--bg); color:var(--ink);
    resize:vertical; margin-bottom:10px; }
  .decision textarea { min-height:44px; }
  .foot { color:var(--muted); font-size:12px; text-align:center; padding:20px; }
  .hidden { display:none !important; }
</style>
</head>
<body>
<header>
  <h1 id="title"></h1>
  <div class="sub" id="subtitle"></div>
  <div class="stats" id="stats"></div>
  <div class="banner hidden" id="banner"></div>
  <div class="toolbar">
    <label class="progress">Type
      <select id="f-type"><option value="">all</option></select>
    </label>
    <label class="progress">Confidence
      <select id="f-conf">
        <option value="">any</option><option>high</option><option>medium</option><option>low</option>
      </select>
    </label>
    <label class="progress"><input type="checkbox" id="f-unresolved"> unresolved only</label>
    <span class="grow"></span>
    <span class="progress"><b id="p-done">0</b> of <b id="p-total">0</b> resolved</span>
    <button id="btn-csv">Export CSV</button>
    <button id="btn-json">Export JSON</button>
    <button id="btn-clear" title="Clears decisions saved in this browser">Clear</button>
  </div>
</header>
<main id="cards"></main>
<div class="foot" id="foot"></div>

<script>
const DATA = /*__DATA__*/;
const CATS = DATA.categories;
const LABELS = DATA.category_labels;
const KEY = "adj:" + DATA.obsid + ":" + DATA.stem;

let store = {};
try { store = JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { store = {}; }
const save = () => localStorage.setItem(KEY, JSON.stringify(store));
const dec = (t) => (store[t] = store[t] || { categories: [], include: "", note: "", rule: "" });
const isResolved = (t) => !!(store[t] && store[t].include);

const esc = (s) => (s == null ? "" : String(s)).replace(/[&<>"']/g,
  c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));

// Highlight the first coder span found inside a turn's text (whitespace-loose).
function highlight(text, spans) {
  let out = esc(text);
  for (const raw of spans) {
    const span = (raw || "").trim();
    if (!span) continue;
    const needle = esc(span);
    const idx = out.toLowerCase().indexOf(needle.toLowerCase());
    if (idx >= 0) {
      out = out.slice(0, idx) + "<mark>" + out.slice(idx, idx + needle.length) +
            "</mark>" + out.slice(idx + needle.length);
      break; // one mark per turn keeps the excerpt readable
    }
  }
  return out;
}

function coderCol(c, s) {
  if (!s || !s.flagged) {
    return `<div class="coder"><h4><span class="dot off"></span>Coder ${esc(c)}</h4>
      <span class="conf">did not flag</span></div>`;
  }
  const cats = (s.categories || []).map(x =>
    `<span class="cat" title="${esc(LABELS[x] || x)}">${esc(x)}</span>`).join("") || "—";
  const note = s.note ? `<div class="note">${esc(s.note)}</div>` : "";
  const span = s.span ? `<div class="span"><q>${esc(s.span)}</q></div>` : "";
  return `<div class="coder flagged"><h4><span class="dot on"></span>Coder ${esc(c)}</h4>
    <div class="cats">${cats}</div>
    <span class="conf">${esc(s.confidence || "no confidence")}</span>
    ${note}${span}</div>`;
}

function card(r) {
  const badgeClass = r.status.startsWith("ONLY") ? "ONLY" : r.status;
  const spans = DATA.coders.map(c => (r.coders[c] && r.coders[c].span) || "").filter(Boolean);
  const ctx = r.context.map(x => {
    const t = x.turn === r.turn;
    const body = t ? highlight(x.text, spans) : esc(x.text);
    return `<div class="row ${t ? "target" : ""}">${t ? "→ " : ""}<span class="spk">${esc(x.speaker)}</span>: ${body}</div>`;
  }).join("");
  const cols = DATA.coders.map(c => coderCol(c, r.coders[c])).join("");
  const d = dec(r.turn);
  const catpick = CATS.map(x =>
    `<label title="${esc(LABELS[x] || x)}"><input type="checkbox" data-cat="${esc(x)}"
      ${d.categories.includes(x) ? "checked" : ""}>${esc(x)}</label>`).join("");
  return `<section class="card ${isResolved(r.turn) ? "resolved" : ""}" data-turn="${r.turn}"
      data-status="${esc(r.status)}" data-conf="${esc(r.max_conf)}" id="turn-${r.turn}">
    <div class="card-head">
      <span class="turn-no">Turn ${r.turn}</span>
      <span class="badge ${badgeClass}">${esc(r.status)}</span>
      <span class="resolved-tag">✓ resolved</span>
    </div>
    <div class="context">${ctx}</div>
    <div class="coders">${cols}</div>
    <div class="decision">
      <p class="lbl">Decision — categories for the gold standard</p>
      <div class="catpick">${catpick}</div>
      <div class="incl">
        <label><input type="radio" name="incl-${r.turn}" value="Y" ${d.include==="Y"?"checked":""}> include (Y)</label>
        <label><input type="radio" name="incl-${r.turn}" value="N" ${d.include==="N"?"checked":""}> exclude (N)</label>
        <label><input type="radio" name="incl-${r.turn}" value="defer" ${d.include==="defer"?"checked":""}> defer</label>
      </div>
      <textarea data-field="note" placeholder="Decision note — why we landed here">${esc(d.note)}</textarea>
      <input class="rule" data-field="rule" placeholder="Rule this establishes (for the codebook)" value="${esc(d.rule)}">
    </div>
  </section>`;
}

function refreshProgress() {
  const done = DATA.rows.filter(r => isResolved(r.turn)).length;
  document.getElementById("p-done").textContent = done;
  document.getElementById("p-total").textContent = DATA.rows.length;
}

function applyFilters() {
  const type = document.getElementById("f-type").value;
  const conf = document.getElementById("f-conf").value;
  const unres = document.getElementById("f-unresolved").checked;
  for (const el of document.querySelectorAll(".card")) {
    const t = +el.dataset.turn;
    const okType = !type || el.dataset.status === type;
    const okConf = !conf || el.dataset.conf === conf;
    const okUnres = !unres || !isResolved(t);
    el.classList.toggle("hidden", !(okType && okConf && okUnres));
  }
}

function render() {
  document.getElementById("title").textContent = "Adjudication — obsid " + DATA.obsid;
  document.getElementById("subtitle").textContent = DATA.subtitle;
  document.getElementById("stats").innerHTML = DATA.stat_chips
    .map(s => `<span class="stat">${esc(s.label)} <b>${esc(s.value)}</b></span>`).join("");
  if (DATA.banner) {
    const b = document.getElementById("banner");
    b.textContent = DATA.banner; b.classList.remove("hidden");
  }
  const typeSel = document.getElementById("f-type");
  [...new Set(DATA.rows.map(r => r.status))].sort().forEach(s => {
    const o = document.createElement("option"); o.value = o.textContent = s; typeSel.appendChild(o);
  });
  document.getElementById("cards").innerHTML = DATA.rows.map(card).join("");
  document.getElementById("foot").textContent =
    "Generated " + DATA.generated_at + " · decisions save automatically in this browser (" +
    KEY + ") · Export to share.";
  refreshProgress();

  document.getElementById("cards").addEventListener("change", (e) => {
    const el = e.target;
    const cardEl = el.closest(".card"); if (!cardEl) return;
    const t = +cardEl.dataset.turn; const d = dec(t);
    if (el.dataset.cat) {
      const set = new Set(d.categories);
      el.checked ? set.add(el.dataset.cat) : set.delete(el.dataset.cat);
      d.categories = CATS.filter(c => set.has(c));
    } else if (el.name === "incl-" + t) {
      d.include = el.value;
    } else if (el.dataset.field) {
      d[el.dataset.field] = el.value;
    }
    save();
    cardEl.classList.toggle("resolved", isResolved(t));
    refreshProgress(); applyFilters();
  });
  document.getElementById("cards").addEventListener("input", (e) => {
    const el = e.target; if (!el.dataset.field) return;
    const cardEl = el.closest(".card"); const t = +cardEl.dataset.turn;
    dec(t)[el.dataset.field] = el.value; save();
  });

  ["f-type","f-conf","f-unresolved"].forEach(id =>
    document.getElementById(id).addEventListener("change", applyFilters));
  document.getElementById("btn-csv").addEventListener("click", exportCSV);
  document.getElementById("btn-json").addEventListener("click", exportJSON);
  document.getElementById("btn-clear").addEventListener("click", () => {
    if (confirm("Clear all decisions saved in this browser for obsid " + DATA.obsid + "?")) {
      store = {}; save(); document.getElementById("cards").innerHTML = DATA.rows.map(card).join("");
      refreshProgress(); applyFilters();
    }
  });
}

function download(name, text, mime) {
  const blob = new Blob([text], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function csvCell(v) {
  v = v == null ? "" : String(v);
  return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
}
function exportCSV() {
  const head = ["obsid","turn","status","decision_categories","decision_include","decision_note","rule_established"];
  const lines = [head.join(",")];
  for (const r of DATA.rows) {
    const d = store[r.turn] || {};
    lines.push([DATA.obsid, r.turn, r.status, (d.categories||[]).join(" "),
      d.include||"", d.note||"", d.rule||""].map(csvCell).join(","));
  }
  download(DATA.stem + "_decisions.csv", lines.join("\r\n"), "text/csv");
}
function exportJSON() {
  download(DATA.stem + "_decisions.json", JSON.stringify({
    obsid: DATA.obsid, coders: DATA.coders, generated_from: DATA.stem,
    exported_at: new Date().toISOString(), decisions: store
  }, null, 2), "application/json");
}

render();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Build a two-coder adjudication worksheet.")
    ap.add_argument("--obsid", required=True)
    ap.add_argument("--coders", nargs=2, default=["1", "2"], metavar=("A", "B"))
    ap.add_argument("--llm", action="store_true", help="Add the llm coding as a third column.")
    ap.add_argument("--context", type=int, default=2, help="Context turns each side (0 to omit).")
    ap.add_argument(
        "--scope",
        choices=["cocovered", "full"],
        default="cocovered",
        help="Worksheet rows: only the range both coders reached (default), or every flag.",
    )
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    args = ap.parse_args()

    obsid = coder.safe_id(args.obsid)
    a_id, b_id = args.coders

    turns, err = coder.load_turns(obsid)
    if err:
        raise SystemExit(err)
    t_turns = teacher_turns(turns)
    last_turn = turns[-1]["turn_num"] if turns else 0

    coder_ids = [a_id, b_id] + (["llm"] if args.llm else [])
    codings = {c: load_coding(obsid, c) for c in coder_ids}
    flags = {c: set(coder.cats_map(codings[c])) for c in coder_ids}
    cats = {c: coder.cats_map(codings[c]) for c in coder_ids}
    scenes = {c: coder.scenes_by_turn(codings[c]) for c in coder_ids}

    # The llm coding always spans the whole transcript; only humans can stop early.
    human_ids = [a_id, b_id]
    reach = {c: attested_through(codings[c]) for c in human_ids}
    cocovered = min(reach.values())
    uncoded_tail = [t for t in t_turns if t > cocovered]

    scope_turns = set(t_turns) if args.scope == "full" else {t for t in t_turns if t <= cocovered}
    universe_n = len(scope_turns)

    a_scoped = flags[a_id] & scope_turns
    b_scoped = flags[b_id] & scope_turns
    stats = irr.binary_agreement(a_scoped, b_scoped, universe_n)
    cat_stats = irr.category_agreement(
        {t: cats[a_id][t] for t in a_scoped},
        {t: cats[b_id][t] for t in b_scoped},
    )

    # Threshold vs. definition: how much of the smaller flag set sits inside the
    # larger one. High containment with unequal sizes means the pair differs on
    # sensitivity, not on what the categories mean.
    small, large = sorted([a_scoped, b_scoped], key=len)
    containment = len(small & large) / len(small) if small else None

    rows = sorted(scope_turns & set().union(*(flags[c] for c in coder_ids)))
    text_by_turn = {t["turn_num"]: t["text"] for t in turns}
    speaker_by_turn = {t["turn_num"]: t["speaker"] for t in turns}

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"obsid{obsid}_{a_id}v{b_id}" + ("_llm" if args.llm else "")

    # --- CSV: one row per disputed turn, with a blank decision column ---------
    csv_path = out_dir / f"{stem}_worksheet.csv"
    fields = ["obsid", "turn", "status"]
    for c in coder_ids:
        fields += [f"c{c}_flagged", f"c{c}_categories", f"c{c}_confidence", f"c{c}_note"]
    fields += ["teacher_turn_text", "decision_categories", "decision_include", "decision_note"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for t in rows:
            row = {
                "obsid": obsid,
                "turn": t,
                "status": status_for(t, flags, cats, coder_ids),
                "teacher_turn_text": text_by_turn.get(t, ""),
                "decision_categories": "",
                "decision_include": "",
                "decision_note": "",
            }
            for c in coder_ids:
                s = scenes[c].get(t)
                row[f"c{c}_flagged"] = "yes" if s else "no"
                row[f"c{c}_categories"] = ",".join(sorted(s.get("categories", []))) if s else ""
                row[f"c{c}_confidence"] = s.get("confidence", "") if s else ""
                row[f"c{c}_note"] = s.get("note", "") if s else ""
            w.writerow(row)

    # --- Markdown: the thing you actually read in the session ----------------
    meta = coder.observation_meta(obsid)
    L = []
    L.append(f"# Adjudication worksheet — obsid {obsid}")
    L.append("")
    L.append(f"Teacher {meta.get('teacher_id') or '?'} · year {meta.get('year') or '?'} · "
             f"{last_turn} turns ({len(t_turns)} teacher) · coders {a_id} vs {b_id}"
             + (" vs llm" if args.llm else ""))
    L.append("")

    L.append("## Coverage")
    L.append("")
    L.append("| coder | flags | attested through | marked complete |")
    L.append("|---|---|---|---|")
    for c in human_ids:
        L.append(f"| {c} | {len(flags[c])} | turn {reach[c]} | "
                 f"{'yes' if codings[c].get('progress', {}).get('completed') else '**no**'} |")
    if args.llm:
        L.append(f"| llm | {len(flags['llm'])} | full transcript | yes |")
    L.append("")
    if uncoded_tail:
        pct = 100 * len(uncoded_tail) / len(t_turns)
        L.append(f"> **{len(uncoded_tail)} teacher turns ({pct:.0f}%) sit past turn {cocovered}, "
                 f"where neither coder has a flag and neither is marked complete.** Treat that "
                 f"range as uncoded, not as agreed-empty. Rows below are restricted to turns "
                 f"1–{cocovered}." if args.scope == "cocovered" else
                 f"> **{len(uncoded_tail)} teacher turns sit past turn {cocovered}.** "
                 f"`--scope full` is in use, so rows past that point reflect one coder's "
                 f"coverage rather than a disagreement.")
        L.append("")

    L.append("## Agreement")
    L.append("")
    L.append(f"Computed over {universe_n} teacher turns"
             + (f" in turns 1–{cocovered}." if args.scope == "cocovered" else " (full transcript)."))
    L.append("")
    L.append("| stat | value |")
    L.append("|---|---|")
    L.append(f"| both flagged | {stats['both']} |")
    L.append(f"| only coder {a_id} | {stats['a_only']} |")
    L.append(f"| only coder {b_id} | {stats['b_only']} |")
    L.append(f"| **positive agreement** (headline) | **{fmt(stats['positive_agreement'])}** |")
    L.append(f"| Cohen's κ | {fmt(stats['cohen_kappa'])} |")
    L.append(f"| PABAK | {fmt(stats['pabak'])} |")
    L.append(f"| raw agreement (inflated) | {fmt(stats['raw_agreement'])} |")
    L.append(f"| category Jaccard, shared turns | {fmt(cat_stats['mean_jaccard'])} |")
    L.append("")
    L.append("Do not report κ alone — see `tools/coder/README.md`.")
    L.append("")

    L.append("### Threshold or definition?")
    L.append("")
    if containment is None:
        L.append("One coder flagged nothing in scope; no diagnostic possible.")
    else:
        n_small, n_large = len(small), len(large)
        L.append(f"Smaller flag set: {n_small}. Larger: {n_large}. "
                 f"Containment of smaller in larger: **{containment:.0%}**.")
        L.append("")
        if containment >= 0.75 and n_large > n_small:
            L.append("> High containment with unequal sizes — this reads as a **threshold** "
                     "difference: one coder requires more evidence before flagging. Settle on "
                     "how strong a cue has to be before it counts, and the category work will "
                     "mostly follow.")
        elif containment < 0.5:
            L.append("> Low containment — the coders are flagging **different turns**, not the "
                     "same turns at different sensitivities. Work through what each category "
                     "covers before touching threshold.")
        else:
            L.append("> Mixed — some threshold gap, some genuine divergence on which turns "
                     "qualify. Expect both conversations.")
    L.append("")
    if cat_stats["per_category"]:
        L.append("Per category (union of flagged turns in scope):")
        L.append("")
        L.append(f"| cat | both | only {a_id} | only {b_id} |")
        L.append("|---|---|---|---|")
        for c, v in sorted(cat_stats["per_category"].items()):
            L.append(f"| {c} | {v['both']} | {v['a_only']} | {v['b_only']} |")
        L.append("")

    L.append("## Turns to resolve")
    L.append("")
    L.append(f"{len(rows)} turns. Work top to bottom; fill in **Decision** as you go, "
             f"then transfer to `{csv_path.name}`.")
    L.append("")

    for t in rows:
        st = status_for(t, flags, cats, coder_ids)
        L.append(f"### Turn {t} — {st}")
        L.append("")
        if args.context:
            for ctx in coder.context_for(turns, t, window=args.context):
                mark = "**→**" if ctx["turn"] == t else "  "
                L.append(f"- {mark} `t{ctx['turn']}` **{ctx['speaker']}**: {ctx['text']}")
        else:
            L.append(f"> **{speaker_by_turn.get(t, '?')}**: {text_by_turn.get(t, '')}")
        L.append("")
        for c in coder_ids:
            s = scenes[c].get(t)
            if not s:
                L.append(f"- **Coder {c}:** did not flag")
                continue
            cl = ", ".join(sorted(s.get("categories", []))) or "—"
            bits = [f"**Coder {c}:** {cl} ({s.get('confidence') or 'no confidence'})"]
            if s.get("note"):
                bits.append(f"  \n  _note:_ {s['note']}")
            q = (s.get("verbatim_quote") or "").strip()
            full = (text_by_turn.get(t) or "").strip()
            if q and q != full:
                bits.append(f"  \n  _span:_ “{q}”")
            L.append("- " + "".join(bits))
        L.append("")
        L.append("**Decision:** categories ______  include in gold standard: Y / N  ")
        L.append("**Rule this establishes:** ____________________________________")
        L.append("")

    md_path = out_dir / f"{stem}_worksheet.md"
    md_path.write_text("\n".join(L), encoding="utf-8")

    stats_path = out_dir / f"{stem}_stats.json"
    coder.write_json(stats_path, {
        "obsid": obsid, "coders": coder_ids, "scope": args.scope,
        "universe_n": universe_n, "cocovered_through": cocovered,
        "uncoded_tail_teacher_turns": len(uncoded_tail),
        "attested_through": reach,
        "binary": stats, "category": cat_stats,
        "containment_of_smaller_in_larger": containment,
    })

    # --- HTML: the interactive board coders discuss and resolve in ------------
    html_ctx = args.context or 2
    conf_rank = {"high": 3, "medium": 2, "low": 1, "": 0, None: 0}
    board_rows = []
    for t in rows:
        row_coders = {}
        confs = []
        for c in coder_ids:
            s = scenes[c].get(t)
            if not s:
                row_coders[c] = {"flagged": False}
                continue
            q = (s.get("verbatim_quote") or "").strip()
            full = (text_by_turn.get(t) or "").strip()
            confs.append(s.get("confidence") or "")
            row_coders[c] = {
                "flagged": True,
                "categories": sorted(s.get("categories", [])),
                "confidence": s.get("confidence") or "",
                "note": s.get("note") or "",
                "span": q if (q and q != full) else "",
            }
        max_conf = max(confs, key=lambda x: conf_rank.get(x, 0)) if confs else ""
        board_rows.append({
            "turn": t,
            "status": status_for(t, flags, cats, coder_ids),
            "max_conf": max_conf,
            "context": [
                {"turn": ctx["turn"], "speaker": ctx["speaker"], "text": ctx["text"]}
                for ctx in coder.context_for(turns, t, window=html_ctx)
            ],
            "coders": row_coders,
        })

    stat_chips = [
        {"label": "positive agreement", "value": fmt(stats["positive_agreement"], 2)},
        {"label": "Cohen's κ", "value": fmt(stats["cohen_kappa"], 2)},
        {"label": "PABAK", "value": fmt(stats["pabak"], 2)},
        {"label": "Jaccard", "value": fmt(cat_stats["mean_jaccard"], 2)},
        {"label": "both flagged", "value": stats["both"]},
        {"label": f"only {a_id}", "value": stats["a_only"]},
        {"label": f"only {b_id}", "value": stats["b_only"]},
    ]
    banner = ""
    if uncoded_tail and args.scope == "cocovered":
        pct = 100 * len(uncoded_tail) / len(t_turns)
        banner = (f"{len(uncoded_tail)} teacher turns ({pct:.0f}%) sit past turn {cocovered}, "
                  f"uncoded by both humans — treated as uncoded, not agreed-empty. "
                  f"Only turns 1–{cocovered} appear below.")
    payload = {
        "obsid": obsid,
        "stem": stem,
        "coders": coder_ids,
        "categories": coder.CATEGORIES,
        "category_labels": CATEGORY_LABELS,
        "subtitle": (f"Teacher {meta.get('teacher_id') or '?'} · year {meta.get('year') or '?'} · "
                     f"{last_turn} turns ({len(t_turns)} teacher) · coders "
                     + " vs ".join(coder_ids) + f" · scope: {args.scope}"),
        "stat_chips": stat_chips,
        "banner": banner,
        "rows": board_rows,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    html_path = build_html(payload, out_dir, stem)

    print(f"obsid {obsid}: {len(rows)} turns to resolve "
          f"({stats['both']} agree-on-flag, {stats['a_only']} only-{a_id}, {stats['b_only']} only-{b_id})")
    if uncoded_tail:
        print(f"WARNING: {len(uncoded_tail)} teacher turns past t{cocovered} are uncoded by both humans.")
    for p in (md_path, csv_path, stats_path, html_path):
        print(f"  wrote {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
