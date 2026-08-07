#!/usr/bin/env python3
"""
Legacy video_id -> OBSID crosswalk.

`data/transcripts/<id>_original.csv` is keyed on the NCTE **video_id**, which
identifies a teacher observed across years -- not an observation. 24 of those 52
ids collide numerically with real OBSIDs, so reading a legacy filename as an
OBSID silently names the wrong class (`309_original.csv` is observation 2204).
Everything derived from those files -- the deficit runs, their reports -- inherits
the mislabel.

This script resolves each legacy file to its true OBSID by **content hash**, not
by name. `data/observation_index.csv` carries a sha256 per archived observation,
so an exact match is proof of identity.

Do NOT use the index's `video_id` column for this: 50 of 52 legacy ids map to
several OBSIDs each (video_id 309 -> obsids 15, 201, 536, 2204, 2467, 2684), so
that column cannot identify which observation a legacy file holds. Only the hash
can.

Read-only with respect to every input. Writes two files:
    data/obsid_crosswalk.csv        the map, one row per legacy transcript
    data/obsid_crosswalk.meta.json  provenance for the map

Usage:
    py -3 scripts/build_obsid_crosswalk.py
    py -3 scripts/build_obsid_crosswalk.py --check   # verify, write nothing
"""

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT_DIR = REPO_ROOT / "data" / "transcripts"
ARCHIVE_DIR = TRANSCRIPT_DIR / "by_obsid"
INDEX_PATH = REPO_ROOT / "data" / "observation_index.csv"
OUT_CSV = REPO_ROOT / "data" / "obsid_crosswalk.csv"
OUT_META = REPO_ROOT / "data" / "obsid_crosswalk.meta.json"

LEGACY_SUFFIX = "_original.csv"

FIELDS = [
    "legacy_id",        # the number in the filename -- an old video_id
    "legacy_file",
    "sha256",
    "obsid",            # true observation, or "" when unresolved
    "match",            # unique | ambiguous | unmatched
    "collides_with_obsid",   # True when legacy_id is itself a valid OBSID
    "teacher_id",
    "year",
    "n_codeable_turns",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_index():
    """obsid -> row, plus sha256 -> [obsid]. The index is the identity authority."""
    if not INDEX_PATH.exists():
        raise SystemExit(f"Missing {INDEX_PATH}; run scripts/build_observation_index.py first.")
    rows = {}
    by_sha = {}
    with open(INDEX_PATH, "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rows[r["obsid"]] = r
            by_sha.setdefault(r["sha256"], []).append(r["obsid"])
    return rows, by_sha


def build_rows():
    index, by_sha = load_index()
    archived = {p.stem for p in ARCHIVE_DIR.glob("*.csv")}
    out = []
    for path in sorted(TRANSCRIPT_DIR.glob(f"*{LEGACY_SUFFIX}")):
        legacy_id = path.name[: -len(LEGACY_SUFFIX)]
        digest = sha256_of(path)
        hits = by_sha.get(digest, [])
        if len(hits) == 1:
            match, obsid = "unique", hits[0]
        elif hits:
            # Two archived observations with identical bytes. Recorded rather
            # than guessed -- picking one would fabricate a provenance claim.
            match, obsid = "ambiguous", ""
        else:
            match, obsid = "unmatched", ""
        meta = index.get(obsid, {}) if obsid else {}
        out.append({
            "legacy_id": legacy_id,
            "legacy_file": path.name,
            "sha256": digest,
            "obsid": obsid,
            "match": match,
            # The dangerous subset: reading this filename as an OBSID lands on a
            # real, different observation rather than simply failing.
            "collides_with_obsid": legacy_id in archived,
            "teacher_id": meta.get("video_id", ""),
            "year": meta.get("year", ""),
            "n_codeable_turns": meta.get("n_codeable_turns", ""),
            "_ambiguous_hits": hits if match == "ambiguous" else [],
        })
    return out


def write_outputs(rows):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in FIELDS})

    counts = {m: sum(1 for r in rows if r["match"] == m) for m in ("unique", "ambiguous", "unmatched")}
    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_by": "scripts/build_obsid_crosswalk.py",
        "method": "sha256 of legacy file matched against observation_index.csv sha256 column",
        "inputs": {
            "observation_index": {
                "path": str(INDEX_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": sha256_of(INDEX_PATH),
            },
            "legacy_glob": f"data/transcripts/*{LEGACY_SUFFIX}",
            "legacy_file_count": len(rows),
        },
        "counts": counts,
        "unmatched": [r["legacy_id"] for r in rows if r["match"] == "unmatched"],
        "ambiguous": {r["legacy_id"]: r["_ambiguous_hits"] for r in rows if r["match"] == "ambiguous"},
        "colliding_ids": sorted((r["legacy_id"] for r in rows if r["collides_with_obsid"]), key=int),
    }
    OUT_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main():
    ap = argparse.ArgumentParser(description="Map legacy video_id transcripts to true OBSIDs by content hash.")
    ap.add_argument("--check", action="store_true", help="Report the mapping without writing files.")
    args = ap.parse_args()

    rows = build_rows()
    counts = {m: sum(1 for r in rows if r["match"] == m) for m in ("unique", "ambiguous", "unmatched")}
    collisions = [r for r in rows if r["collides_with_obsid"]]

    print(f"Legacy transcripts : {len(rows)}")
    print(f"  resolved uniquely: {counts['unique']}")
    print(f"  ambiguous        : {counts['ambiguous']}")
    print(f"  unmatched        : {counts['unmatched']}"
          + (f"  ({', '.join(r['legacy_id'] for r in rows if r['match'] == 'unmatched')})"
             if counts["unmatched"] else ""))
    print(f"  filename collides with a real OBSID: {len(collisions)}")
    for r in collisions[:5]:
        print(f"      {r['legacy_file']} is actually observation {r['obsid'] or '?'}")
    if len(collisions) > 5:
        print(f"      ... and {len(collisions) - 5} more")

    if args.check:
        print("\n--check: nothing written.")
        return

    meta = write_outputs(rows)
    print(f"\nWrote {OUT_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {OUT_META.relative_to(REPO_ROOT)}  (generated_at {meta['generated_at']})")


if __name__ == "__main__":
    main()
