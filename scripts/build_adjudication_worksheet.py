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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools" / "coder"))

import app as coder  # noqa: E402
import irr  # noqa: E402

OUT_DIR = REPO_ROOT / "data" / "adjudication"


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

    print(f"obsid {obsid}: {len(rows)} turns to resolve "
          f"({stats['both']} agree-on-flag, {stats['a_only']} only-{a_id}, {stats['b_only']} only-{b_id})")
    if uncoded_tail:
        print(f"WARNING: {len(uncoded_tail)} teacher turns past t{cocovered} are uncoded by both humans.")
    for p in (md_path, csv_path, stats_path):
        print(f"  wrote {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
