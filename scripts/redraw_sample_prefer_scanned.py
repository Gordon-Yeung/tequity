#!/usr/bin/env python3
"""
Re-draw the coding sample to prefer observations the LLM pipeline has already scanned.

`one_per_teacher.csv` draws one observation per teacher at random (seed 20260724).
The deficit pipeline separately analysed 50 observations -- covering 50 teachers
who are all in the sample, but for 40 of them the draw had picked a *different*
class by the same teacher. Result: LLM coverage on the right teachers, the wrong
observations.

This swaps those 40 rows to the scanned observation. It preserves the
one-per-teacher property (a swap, never an addition) and touches only teachers
that have a scanned observation; the other 269 rows keep their seeded draw.

TRADE-OFF THE RESEARCHER MUST DECLARE: after this, selection for those 40
teachers is no longer random -- it depends on which classes happened to be
extracted into `data/transcripts/*_original.csv` first. The `selection` column
marks exactly which rows were overridden so the effect is auditable and can be
modelled or reverted.

Idempotent: re-running is a no-op once the preferred rows are in place.

ORDERING: `build_observation_index.py` *writes* this manifest from scratch and
does not know about scanned observations. If you re-run it, re-run this after.

Usage:
    py -3 scripts/redraw_sample_prefer_scanned.py --dry-run
    py -3 scripts/redraw_sample_prefer_scanned.py
"""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPO_ROOT / "data" / "samples" / "one_per_teacher.csv"
META_PATH = REPO_ROOT / "data" / "samples" / "one_per_teacher.meta.json"
SWAPLOG_PATH = REPO_ROOT / "data" / "samples" / "one_per_teacher.swaps.csv"
INDEX_PATH = REPO_ROOT / "data" / "observation_index.csv"
CROSSWALK = REPO_ROOT / "data" / "obsid_crosswalk.csv"

BASE_FIELDS = ["video_id", "obsid", "year", "n_observations_for_teacher",
               "n_codeable_turns", "n_teacher_turns", "ambiguous_only", "seed"]
# Added so the manifest documents its own provenance row by row. Readers that
# only take `obsid` (app.py, export_observation.py) are unaffected.
FIELDS = BASE_FIELDS + ["selection"]

SEEDED, PREFERRED = "seeded_draw", "preferred_scanned"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description="Prefer already-scanned observations in the coding sample.")
    ap.add_argument("--dry-run", action="store_true", help="Report the swaps without writing.")
    args = ap.parse_args()

    for p in (SAMPLE_PATH, INDEX_PATH, CROSSWALK):
        if not p.exists():
            raise SystemExit(f"Missing {p.relative_to(REPO_ROOT)}")

    index = {r["obsid"]: r for r in read_csv(INDEX_PATH)}
    rows = read_csv(SAMPLE_PATH)

    # Scanned observations, grouped by the teacher who owns them.
    scanned_by_teacher = defaultdict(list)
    for r in read_csv(CROSSWALK):
        obsid = r["obsid"]
        if obsid and obsid in index:
            scanned_by_teacher[index[obsid]["video_id"]].append(obsid)

    out, swaps, multi = [], [], []
    for r in rows:
        teacher = r["video_id"]
        candidates = sorted(scanned_by_teacher.get(teacher, []), key=int)
        row = {k: r.get(k, "") for k in BASE_FIELDS}

        if not candidates:
            row["selection"] = SEEDED
            out.append(row)
            continue

        if len(candidates) > 1:
            # No teacher currently has two scanned observations; if that changes,
            # record it rather than silently taking the first.
            multi.append({"video_id": teacher, "candidates": candidates})
        target = candidates[0]

        if target == r["obsid"]:
            # Draw already landed on the scanned observation -- still a seeded
            # draw, not an override.
            row["selection"] = SEEDED
            out.append(row)
            continue

        meta = index[target]
        swaps.append({"video_id": teacher, "from_obsid": r["obsid"], "to_obsid": target,
                      "from_turns": r.get("n_codeable_turns", ""),
                      "to_turns": meta.get("n_codeable_turns", "")})
        row.update({
            "obsid": target,
            "year": meta.get("year", ""),
            "n_codeable_turns": meta.get("n_codeable_turns", ""),
            "n_teacher_turns": meta.get("n_teacher_turns", ""),
            # Teacher-level facts carry over: the same teacher, a different class.
            "n_observations_for_teacher": r.get("n_observations_for_teacher", ""),
            "ambiguous_only": r.get("ambiguous_only", ""),
            "seed": r.get("seed", ""),
            "selection": PREFERRED,
        })
        out.append(row)

    obsids = [r["obsid"] for r in out]
    teachers = [r["video_id"] for r in out]
    assert len(obsids) == len(set(obsids)), "re-draw produced a duplicate OBSID"
    assert len(teachers) == len(set(teachers)), "re-draw broke the one-per-teacher property"
    assert len(out) == len(rows), "re-draw changed the sample size"

    n_pref = sum(1 for r in out if r["selection"] == PREFERRED)
    n_cov = sum(1 for r in out if r["obsid"] in
                {o for v in scanned_by_teacher.values() for o in v})
    print(f"Sample rows            : {len(out)} (unchanged)")
    print(f"One per teacher        : yes")
    print(f"Rows swapped           : {len(swaps)}")
    print(f"Rows already on target : {n_cov - n_pref}")
    print(f"Observations with LLM coverage after re-draw: {n_cov}")
    for s in swaps[:8]:
        print(f"    teacher {s['video_id']}: {s['from_obsid']} -> {s['to_obsid']}"
              f"  ({s['from_turns']} -> {s['to_turns']} codeable turns)")
    if len(swaps) > 8:
        print(f"    ... and {len(swaps) - 8} more")
    if multi:
        print(f"  NOTE: {len(multi)} teachers have >1 scanned observation; took the lowest OBSID.")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return

    before_sha = sha256_of(SAMPLE_PATH)
    with open(SAMPLE_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    with open(SWAPLOG_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["video_id", "from_obsid", "to_obsid", "from_turns", "to_turns"])
        w.writeheader()
        w.writerows(swaps)

    META_PATH.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_by": "scripts/redraw_sample_prefer_scanned.py",
        "rule": "For each teacher with an observation already scanned by the deficit "
                "pipeline, select that observation instead of the seeded draw. All other "
                "rows keep their seeded draw. One observation per teacher is preserved.",
        "randomness_caveat": "The 'preferred_scanned' rows are NOT random. They were "
                             "selected because those classes were extracted into "
                             "data/transcripts/*_original.csv before the archive existed. "
                             "Declare this in any analysis that treats the sample as random.",
        "base_seed": sorted({r.get("seed", "") for r in rows}),
        "inputs": {
            "sample_before_sha256": before_sha,
            "observation_index_sha256": sha256_of(INDEX_PATH),
            "obsid_crosswalk_sha256": sha256_of(CROSSWALK),
        },
        "counts": {
            "rows": len(out),
            "swapped": len(swaps),
            "seeded_draw": len(out) - n_pref,
            "preferred_scanned": n_pref,
            "with_llm_coverage": n_cov,
        },
        "teachers_with_multiple_scanned": multi,
    }, indent=2) + "\n", encoding="utf-8")

    print(f"\nWrote {SAMPLE_PATH.relative_to(REPO_ROOT)}")
    print(f"Wrote {SWAPLOG_PATH.relative_to(REPO_ROOT)}  ({len(swaps)} swaps)")
    print(f"Wrote {META_PATH.relative_to(REPO_ROOT)}")
    print("Revert with: git checkout -- data/samples/one_per_teacher.csv")


if __name__ == "__main__":
    main()
