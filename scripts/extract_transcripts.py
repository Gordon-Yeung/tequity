#!/usr/bin/env python3
"""
Extract single-lesson transcripts from the NCTE utterances CSV.

BUG FIX (2026-07-17)
--------------------
The previous version grouped rows by ``video_id`` and wrote one file per video.
But in the NCTE source a single ``video_id`` bundles MANY distinct lessons, each
identified by ``OBSID``. Grouping by ``video_id`` therefore concatenated several
unrelated lessons into one ``<video_id>_original.csv`` (e.g. 309 held 6 lessons,
with 5 separate "good morning everyone" openings). The true per-lesson key is
``OBSID`` (confirmed by ``comb_idx == "<OBSID>_<turn_idx>"``).

This script now:
  1. Archives EVERY lesson of each processed video to
     ``data/transcripts/by_obsid/<OBSID>.csv`` (a full, lossless audit trail).
  2. Writes the canonical ``data/transcripts/<video_id>_original.csv`` using only
     the FIRST OBSID seen for that video_id. "First OBSID" is the convention
     already established by the two hand-prepared Study 1 files
     (706 -> OBSID 2119, 543 -> OBSID 2961) and by the 309 human coding, which
     coded OBSID 2204 -- the first lesson under video_id 309.

Output schema: ``speaker,cleaned_text`` (what app.py and deficit_analysis expect).

706_original.csv and 543_original.csv are left untouched: they are the
pre-existing, already-correct single-lesson Study 1 files (and use their own
column schemas). Their sibling lessons are still archived under by_obsid/ if
those video_ids fall in the processed set.
"""
import csv
from collections import OrderedDict, defaultdict
from pathlib import Path

# --- paths (repo-relative; override SOURCE_CSV if the source lives elsewhere) --
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "transcripts"
ARCHIVE_DIR = OUTPUT_DIR / "by_obsid"

# The NCTE source is not committed to the repo (too large / not redistributable).
# Point this at your local copy.
SOURCE_CSV = Path.home() / "Downloads" / "ncte_single_utterances.csv"

# Same selection the original batch used: the first 50 video_ids in sorted order.
NUM_VIDEOS = 50

# These video_ids already have hand-prepared, single-lesson Study 1 files with
# their own column schemas. Never overwrite their canonical _original.csv.
PROTECTED_VIDEO_IDS = {"706", "543"}


def read_source(path: Path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_turns(path: Path, rows):
    """Write [{speaker, cleaned_text}, ...] rows with a stable schema."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["speaker", "cleaned_text"])
        for r in rows:
            w.writerow([r["speaker"], r["cleaned_text"]])


def main():
    if not SOURCE_CSV.exists():
        raise SystemExit(
            f"Source CSV not found: {SOURCE_CSV}\n"
            "Edit SOURCE_CSV at the top of this script to point at your local copy."
        )

    print(f"Reading {SOURCE_CSV} ...")
    rows = read_source(SOURCE_CSV)
    print(f"  {len(rows)} utterances")

    # video_id -> ordered unique OBSIDs (first-seen order == source order)
    obsids_by_video = defaultdict(lambda: OrderedDict())
    # (video_id, OBSID) -> list of {speaker, cleaned_text} in source order
    turns_by_obs = defaultdict(list)
    for r in rows:
        vid, obs = r["video_id"], r["OBSID"]
        obsids_by_video[vid][obs] = None
        turns_by_obs[(vid, obs)].append(
            {"speaker": r["speaker"], "cleaned_text": r["cleaned_text"]}
        )

    targets = sorted(obsids_by_video)[:NUM_VIDEOS]
    print(f"Found {len(obsids_by_video)} unique video_ids; processing first {len(targets)}.")

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    n_archived = 0
    for i, vid in enumerate(targets, 1):
        obsids = list(obsids_by_video[vid])

        # 1) Archive every lesson under by_obsid/<OBSID>.csv
        for obs in obsids:
            write_turns(ARCHIVE_DIR / f"{obs}.csv", turns_by_obs[(vid, obs)])
            n_archived += 1

        # 2) Canonical file = first OBSID only
        first_obs = obsids[0]
        canonical = turns_by_obs[(vid, first_obs)]
        note = ""
        if vid in PROTECTED_VIDEO_IDS:
            note = "  [PROTECTED: canonical _original.csv left untouched]"
        else:
            write_turns(OUTPUT_DIR / f"{vid}_original.csv", canonical)

        print(
            f"{i:2d}. video {vid}: {len(obsids)} lesson(s) "
            f"-> canonical = OBSID {first_obs} ({len(canonical)} turns){note}"
        )

    print(
        f"\nDone. Rewrote canonical files for "
        f"{len([v for v in targets if v not in PROTECTED_VIDEO_IDS])} videos; "
        f"archived {n_archived} lessons to {ARCHIVE_DIR.relative_to(REPO_ROOT)}/."
    )


if __name__ == "__main__":
    main()
