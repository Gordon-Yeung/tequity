#!/usr/bin/env python3
"""
Export a self-describing copy of one or more observations.

The canonical archive (``data/transcripts/by_obsid/<OBSID>.csv``) deliberately
holds ``speaker,cleaned_text`` and nothing else: one key per file, bytes frozen,
so turn numbering can never drift under existing human coding. Identity lives in
``data/observation_index.csv`` and is joined in when needed.

That's the right tradeoff inside the repo and the wrong one when handing a single
file to someone who doesn't have the repo. This writes an enriched *copy* to
``data/exports/`` with the identifiers embedded. It never touches the archive.

    python scripts/export_observation.py 2204
    python scripts/export_observation.py --sample          # all 319 in the sample
    python scripts/export_observation.py 2204 2684 --raw   # include raw `text`

NOTE ON --raw: the pipeline's loader prefers a ``text`` column over
``cleaned_text``, and quote verification is done against *cleaned* text (which has
punctuation stripped). An export carrying ``text`` must therefore never be fed
back into the pipeline -- every recorded quote would fail to match. The column is
named ``raw_text`` here for exactly that reason; don't rename it to ``text``.
"""
import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = REPO_ROOT / "data" / "transcripts" / "by_obsid"
INDEX_PATH = REPO_ROOT / "data" / "observation_index.csv"
SAMPLE_PATH = REPO_ROOT / "data" / "samples" / "one_per_teacher.csv"
EXPORT_DIR = REPO_ROOT / "data" / "exports"
SOURCE_CSV = Path.home() / "Downloads" / "ncte_single_utterances.csv"


def load_index():
    if not INDEX_PATH.exists():
        sys.exit(f"Missing {INDEX_PATH.relative_to(REPO_ROOT)} -- run build_observation_index.py first.")
    with open(INDEX_PATH, "r", encoding="utf-8-sig", newline="") as f:
        return {r["obsid"]: r for r in csv.DictReader(f)}


def load_raw_text(obsids):
    """OBSID -> [raw text, ...] in source order. Only read when --raw is used."""
    if not SOURCE_CSV.exists():
        sys.exit(f"--raw needs the source CSV: {SOURCE_CSV}")
    wanted = set(obsids)
    out = {o: [] for o in wanted}
    with open(SOURCE_CSV, "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["OBSID"] in wanted:
                out[r["OBSID"]].append(r["text"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("obsids", nargs="*", help="OBSIDs to export")
    ap.add_argument("--sample", action="store_true",
                    help="export every observation in one_per_teacher.csv")
    ap.add_argument("--raw", action="store_true",
                    help="add a raw_text column from the source CSV")
    args = ap.parse_args()

    index = load_index()
    obsids = list(args.obsids)
    if args.sample:
        if not SAMPLE_PATH.exists():
            return print(f"No sample manifest at {SAMPLE_PATH}", file=sys.stderr) or 1
        with open(SAMPLE_PATH, "r", encoding="utf-8-sig", newline="") as f:
            obsids += [r["obsid"] for r in csv.DictReader(f)]
    if not obsids:
        ap.error("give at least one OBSID, or --sample")

    unknown = [o for o in obsids if o not in index]
    if unknown:
        return print(f"Not in the index: {unknown}", file=sys.stderr) or 1

    raw = load_raw_text(obsids) if args.raw else {}
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    for obsid in obsids:
        meta = index[obsid]
        src = ARCHIVE_DIR / f"{obsid}.csv"
        if not src.exists():
            print(f"  skip {obsid}: {src.name} not found", file=sys.stderr)
            continue

        with open(src, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

        cols = ["obsid", "teacher_id", "year", "turn", "speaker", "cleaned_text"]
        if args.raw:
            cols.append("raw_text")

        out_path = EXPORT_DIR / f"obs{obsid}_teacher{meta['video_id'].replace('|', '-')}.csv"
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for i, r in enumerate(rows, start=1):
                # `turn` is the pipeline's turn_num: enumerate over ALL rows from 1.
                # Rows with no speaker/text still consume a number, so the sequence
                # has gaps -- that is what human coding and LLM scenes refer to.
                rec = [obsid, meta["video_id"], meta["year"], i,
                       r.get("speaker", ""), r.get("cleaned_text", "")]
                if args.raw:
                    texts = raw.get(obsid, [])
                    rec.append(texts[i - 1] if i - 1 < len(texts) else "")
                w.writerow(rec)
        print(f"  {out_path.relative_to(REPO_ROOT)}  ({len(rows)} rows)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
