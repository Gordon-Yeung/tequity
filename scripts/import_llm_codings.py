#!/usr/bin/env python3
"""
Load the LLM's scenes into the coding tool as a third coder, in bulk.

The Compare & Adjudicate screen treats `data/human_coding/<obsid>/llm.json` as a
coder alongside the humans, but that file only appears when someone clicks
"Import LLM scenes" for that one observation. This writes it for every
observation that has scenes in the newest relabelled run.

Reuses `build_llm_coding()` from tools/coder/app.py rather than reimplementing
the conversion -- two versions of "what the LLM coder looks like" would drift and
the Compare screen would end up disagreeing with itself.

Only `llm.json` is ever written. Human codings are never touched, and an existing
llm.json is left alone unless --overwrite is given.

Usage:
    py -3 scripts/import_llm_codings.py --dry-run
    py -3 scripts/import_llm_codings.py
    py -3 scripts/import_llm_codings.py --overwrite   # refresh after a new run
"""

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools" / "coder"))

import app as coder  # noqa: E402

OBSID_RUNS = REPO_ROOT / "data" / "deficit_scenes_obsid"


def observations_with_scenes():
    """[(obsid, n_scenes)] from the newest relabelled run's summary."""
    runs = sorted((d for d in OBSID_RUNS.glob("run_*") if d.is_dir()), reverse=True)
    summary = next((r / "run_summary.csv" for r in runs if (r / "run_summary.csv").exists()), None)
    if summary is None:
        raise SystemExit("No relabelled run found. Run scripts/relabel_deficit_run.py --all first.")
    with open(summary, "r", encoding="utf-8-sig", newline="") as f:
        rows = [(r["obsid"], int(r.get("scenes_found") or 0)) for r in csv.DictReader(f)]
    return summary.parent.name, [(o, n) for o, n in rows if n]


def main():
    ap = argparse.ArgumentParser(description="Bulk-import LLM scenes as the 'llm' coder.")
    ap.add_argument("--dry-run", action="store_true", help="Report without writing.")
    ap.add_argument("--overwrite", action="store_true", help="Replace an existing llm.json.")
    args = ap.parse_args()

    run_name, targets = observations_with_scenes()
    print(f"Newest relabelled run : {run_name}")
    print(f"Observations with scenes: {len(targets)}\n")

    wrote = skipped = missing = 0
    for obsid, n in targets:
        dest = coder.coder_path(obsid, "llm")
        if dest.exists() and not args.overwrite:
            skipped += 1
            continue
        data, src = coder.build_llm_coding(obsid)
        if data is None:
            print(f"  obsid {obsid}: NO SOURCE FILE resolved (expected {n} scenes)")
            missing += 1
            continue
        if len(data["scenes"]) != n:
            # A mismatch would mean the summary and the scene file disagree.
            print(f"  obsid {obsid}: WARNING summary says {n} scenes, source yields {len(data['scenes'])}")
        if not args.dry_run:
            coder.write_json(dest, data)
        wrote += 1

    verb = "would write" if args.dry_run else "wrote"
    print(f"{verb:>12} : {wrote}")
    print(f"{'skipped':>12} : {skipped}  (llm.json already present; use --overwrite to refresh)")
    if missing:
        print(f"{'unresolved':>12} : {missing}")
    if args.dry_run:
        print("\n--dry-run: nothing written.")
    else:
        total = len(list((REPO_ROOT / "data" / "human_coding").glob("*/llm.json")))
        print(f"\nllm.json now present for {total} observations.")
        print("Revert with: git clean -n data/human_coding   (inspect first)")


if __name__ == "__main__":
    main()
