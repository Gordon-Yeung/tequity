#!/usr/bin/env python3
"""
Build the observation index and draw the one-observation-per-teacher sample (Option B).

WHY THIS EXISTS
---------------
``extract_transcripts.py`` archives lessons for only the first 50 ``video_id``s
(string-sorted) and picks each canonical file as "the first OBSID seen in source
row order". Two problems with that:

  1. Coverage. The source holds 1,660 observations across 319 ``video_id``s; the
     archive holds 237 across 50, and only 52 were ever scanned (~3%).
  2. Determinism. "First seen in source row order" silently re-points the
     canonical file if the source CSV is ever re-exported with different row
     ordering -- which would shift turn numbers out from under existing human
     coding.

WHAT ``video_id`` ACTUALLY IS
-----------------------------
Not a video. 192 of 319 ``video_id``s span more than one ``year`` (80 span all
three) while no OBSID spans a year -- so ``video_id`` groups a teacher/participant
observed repeatedly, and OBSID is the single observation session. Observations are
therefore nested within teachers, and one-per-teacher is what makes the sample a
set of independent units.

WHAT THIS SCRIPT WRITES
-----------------------
  data/transcripts/by_obsid/<OBSID>.csv   every observation (1,660), lossless
  data/observation_index.csv              per-observation metadata + sha256
  data/samples/one_per_teacher.csv        the 319 seeded random selections

TURN-NUMBERING CONTRACT (do not break)
--------------------------------------
``deficit_analysis.load_transcript`` numbers turns by enumerating *every* CSV row
from 1; rows missing a speaker or text are skipped from the returned list but
still consume an index (hence the documented gaps). Every source row for an OBSID
must therefore be written, in source order, or existing human coding silently
misaligns. This script re-verifies the 237 pre-existing archive files are
byte-identical after regeneration and aborts if any differ.
"""
import csv
import hashlib
import io
import random
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "transcripts"
ARCHIVE_DIR = OUTPUT_DIR / "by_obsid"
INDEX_PATH = REPO_ROOT / "data" / "observation_index.csv"
SAMPLE_PATH = REPO_ROOT / "data" / "samples" / "one_per_teacher.csv"

# The NCTE source is not committed (too large / not redistributable).
SOURCE_CSV = Path.home() / "Downloads" / "ncte_single_utterances.csv"

# Fixed so the draw is reproducible. Changing it draws a different sample --
# treat that as a new sample, not a re-run of this one.
SAMPLE_SEED = 20260724

# Study 1's hand-prepared canonical files use their own column schemas and are
# never rewritten here. Their observations are still archived and indexed.
PROTECTED_VIDEO_IDS = {"706", "543"}

# csv.field_size_limit guard: utterances are short, but a malformed quote in a
# 113MB file shouldn't kill the run with an opaque error.
csv.field_size_limit(10_000_000)


def render_csv(rows) -> bytes:
    """Serialize [(speaker, cleaned_text), ...] exactly as extract_transcripts.py did.

    Byte-for-byte compatibility with the existing archive is the point: csv.writer
    with newline="" emits \\r\\n, and that is what the committed files contain.
    """
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    w.writerow(["speaker", "cleaned_text"])
    for speaker, text in rows:
        w.writerow([speaker, text])
    return buf.getvalue().encode("utf-8")


def main() -> int:
    if not SOURCE_CSV.exists():
        print(f"Source CSV not found: {SOURCE_CSV}", file=sys.stderr)
        print("Edit SOURCE_CSV at the top of this script.", file=sys.stderr)
        return 1

    print(f"Reading {SOURCE_CSV} ...")
    rows_by_obs = defaultdict(list)          # OBSID -> [(speaker, cleaned_text), ...]
    videos_by_obs = defaultdict(set)         # OBSID -> {video_id}
    years_by_obs = defaultdict(set)          # OBSID -> {year}
    obsids_by_video = defaultdict(OrderedDict)  # video_id -> OBSIDs, first-seen order
    n_rows = 0

    with open(SOURCE_CSV, "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            n_rows += 1
            obs, vid = r["OBSID"], r["video_id"]
            rows_by_obs[obs].append((r["speaker"], r["cleaned_text"]))
            videos_by_obs[obs].add(vid)
            years_by_obs[obs].add(r["year"])
            obsids_by_video[vid][obs] = None

    print(f"  {n_rows:,} utterances | {len(rows_by_obs):,} observations | "
          f"{len(obsids_by_video):,} video_ids")

    # --- Archive every observation, verifying the existing files don't move ----
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    drift = []
    written = 0
    for obs in sorted(rows_by_obs):
        payload = render_csv(rows_by_obs[obs])
        path = ARCHIVE_DIR / f"{obs}.csv"
        if path.exists() and path.read_bytes() != payload:
            drift.append(obs)
            continue
        path.write_bytes(payload)
        written += 1

    if drift:
        print(f"\nABORT: {len(drift)} existing archive file(s) would change content.",
              file=sys.stderr)
        print("Turn numbers in these observations would shift and any human coding "
              "against them would silently misalign.", file=sys.stderr)
        print(f"  affected OBSIDs: {sorted(drift)[:20]}", file=sys.stderr)
        return 2

    print(f"  archived {written:,} observations to {ARCHIVE_DIR.relative_to(REPO_ROOT)}/ "
          f"(pre-existing files verified byte-identical)")

    # --- Index -----------------------------------------------------------------
    # A "codeable" turn is one load_transcript() would return: speaker and text
    # both non-empty. n_rows is what turn numbers are drawn from, so both are
    # recorded -- the gap between them is the gap in the turn numbering.
    shared = sorted(o for o, v in videos_by_obs.items() if len(v) > 1)

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["obsid", "video_id", "year", "n_rows", "n_codeable_turns",
                    "n_teacher_turns", "n_chars", "shared_video_id", "sha256"])
        for obs in sorted(rows_by_obs, key=lambda x: (len(x), x)):
            rows = rows_by_obs[obs]
            codeable = [(s, t) for s, t in rows if s.strip() and t.strip()]
            w.writerow([
                obs,
                "|".join(sorted(videos_by_obs[obs])),
                "|".join(sorted(years_by_obs[obs])),
                len(rows),
                len(codeable),
                sum(1 for s, _ in codeable if s.strip().lower() == "teacher"),
                sum(len(t) for _, t in codeable),
                "yes" if obs in shared else "",
                hashlib.sha256(render_csv(rows)).hexdigest(),
            ])
    print(f"  wrote {INDEX_PATH.relative_to(REPO_ROOT)}")

    # --- One-observation-per-teacher sample ------------------------------------
    # Random, not first-by-source-order, so the draw does not depend on how the
    # source CSV happens to be sorted. Sorted iteration + fixed seed makes it
    # reproducible.
    rng = random.Random(SAMPLE_SEED)
    selection = []
    for vid in sorted(obsids_by_video):
        candidates = sorted(obsids_by_video[vid])
        # An OBSID claimed by two video_ids is ambiguous evidence for either
        # teacher; prefer an unambiguous one when the teacher has another.
        unambiguous = [o for o in candidates if o not in shared]
        pool = unambiguous or candidates
        selection.append((vid, rng.choice(pool), len(candidates), bool(unambiguous)))

    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SAMPLE_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["video_id", "obsid", "year", "n_observations_for_teacher",
                    "n_codeable_turns", "n_teacher_turns", "ambiguous_only", "seed"])
        for vid, obs, n_obs, ok in selection:
            rows = rows_by_obs[obs]
            codeable = [(s, t) for s, t in rows if s.strip() and t.strip()]
            w.writerow([
                vid, obs, "|".join(sorted(years_by_obs[obs])), n_obs,
                len(codeable),
                sum(1 for s, _ in codeable if s.strip().lower() == "teacher"),
                "" if ok else "yes",
                SAMPLE_SEED,
            ])
    print(f"  wrote {SAMPLE_PATH.relative_to(REPO_ROOT)} "
          f"({len(selection)} observations, seed {SAMPLE_SEED})")

    if shared:
        print(f"\nNote: {len(shared)} OBSID(s) claimed by more than one video_id: {shared}")
    protected_obs = {o for o in rows_by_obs if videos_by_obs[o] & PROTECTED_VIDEO_IDS}
    print(f"Note: {len(protected_obs)} observation(s) belong to Study 1 video_ids "
          f"{sorted(PROTECTED_VIDEO_IDS)}; their *_original.csv files were not touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
