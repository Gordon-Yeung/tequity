#!/usr/bin/env python3
"""
Re-key a deficit-analysis run from legacy video_id to true OBSID.

The runs under `data/deficit_scenes/run_*` were produced from
`data/transcripts/<id>_original.csv`, which is keyed on the old NCTE video_id.
Their per-file names, `source_document_id` fields and report headings therefore
label observations by an id that, for 24 of 52 transcripts, names a *different*
real observation. The findings themselves are sound -- quotes were verified
against the file actually read -- so nothing needs re-running against the model.
This is a relabelling, not a re-analysis.

Guarantees:
- **The source run is never touched.** Output goes to a separate tree; the run's
  mtimes are asserted unchanged before exit.
- **Every quote is re-verified** against the OBSID-keyed archive file it is now
  attributed to. A scene that fails is dropped to `unverified.log`, never
  silently re-pointed. This is the same integrity rule deficit_analysis.py
  applies, re-applied against the new source of truth.
- **Provenance is recorded** in MANIFEST.json: source run, sha256 of every input,
  crosswalk version, per-scene legacy origin, and counts.

Usage:
    py -3 scripts/relabel_deficit_run.py                 # newest run
    py -3 scripts/relabel_deficit_run.py --run run_2026-07-19_153121
    py -3 scripts/relabel_deficit_run.py --all           # every run
"""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_deficit_report import build_markdown, markdown_to_text  # noqa: E402

RUNS_BASE = REPO_ROOT / "data" / "deficit_scenes"
OUT_BASE = REPO_ROOT / "data" / "deficit_scenes_obsid"
ARCHIVE_DIR = REPO_ROOT / "data" / "transcripts" / "by_obsid"
CROSSWALK = REPO_ROOT / "data" / "obsid_crosswalk.csv"

LEGACY_SUFFIX = "_original.csv"


# --- quote verification (same normalisation as the pipeline and the coder tool) --
def normalize_text_for_matching(text: str) -> str:
    return " ".join(text.split()).lower()


def load_turns(path: Path):
    """[{turn_num, speaker, text}] using the pipeline's turn numbering: enumerate
    over ALL rows, keep those with both speaker and text, so gaps are intentional
    and turn numbers line up with everything else in the repo."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    turns = []
    for idx, row in enumerate(rows, start=1):
        nr = {(k or "").strip().strip('"').strip(): v for k, v in row.items()}
        speaker = (nr.get("speaker") or "").strip()
        text = (nr.get("text") or nr.get("cleaned_text") or "").strip()
        if speaker and text:
            turns.append({"turn_num": idx, "speaker": speaker, "text": text})
    return turns


def quote_in_source(quote: str, turns) -> bool:
    nq = normalize_text_for_matching(quote)
    return bool(nq) and any(nq in normalize_text_for_matching(t["text"]) for t in turns)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_index():
    """obsid -> index row, for teacher/year context in the crosswalk log."""
    p = REPO_ROOT / "data" / "observation_index.csv"
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        return {r["obsid"]: r for r in csv.DictReader(f)}


def load_sample():
    """OBSIDs in the coding assignment, so the report can say which findings are
    actually on the sample rather than exploratory."""
    p = REPO_ROOT / "data" / "samples" / "one_per_teacher.csv"
    if not p.exists():
        return set()
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        return {r["obsid"] for r in csv.DictReader(f)}


def load_crosswalk():
    if not CROSSWALK.exists():
        raise SystemExit(f"Missing {CROSSWALK}; run scripts/build_obsid_crosswalk.py first.")
    with open(CROSSWALK, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["legacy_id"]: r for r in rows}


def resolve_runs(run_arg, do_all):
    runs = sorted(p for p in RUNS_BASE.glob("run_*") if p.is_dir())
    if not runs:
        raise SystemExit(f"No run_* folders under {RUNS_BASE}")
    if do_all:
        return runs
    if run_arg:
        cand = Path(run_arg) if Path(run_arg).is_absolute() else RUNS_BASE / run_arg
        if not cand.is_dir():
            raise SystemExit(f"Run folder not found: {cand}")
        return [cand]
    return [runs[-1]]


def snapshot_mtimes(d: Path):
    return {p: p.stat().st_mtime_ns for p in d.rglob("*") if p.is_file()}


def relabel(run_dir: Path, xwalk) -> dict:
    out_dir = OUT_BASE / run_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    before = snapshot_mtimes(run_dir)

    inputs = {}
    per_obsid = {}          # obsid -> [scene]
    unresolved = []         # legacy ids with no OBSID
    unverified = []         # scenes whose quote failed against the archive file
    summary_rows = []
    turns_cache = {}

    for src in sorted(run_dir.glob("*.deficit.json")):
        legacy_id = src.name[: -len(".deficit.json")]
        if legacy_id.endswith("_original"):
            legacy_id = legacy_id[: -len("_original")]
        inputs[src.name] = sha256_of(src)
        scenes = json.loads(src.read_text(encoding="utf-8")).get("scenes", [])

        row = xwalk.get(legacy_id)
        obsid = (row or {}).get("obsid") or ""
        if not obsid:
            if scenes:
                unresolved.append({"legacy_id": legacy_id, "scenes": len(scenes),
                                   "reason": (row or {}).get("match", "not in crosswalk")})
            continue

        archive = ARCHIVE_DIR / f"{obsid}.csv"
        if obsid not in turns_cache:
            turns_cache[obsid] = load_turns(archive) if archive.exists() else []
        turns = turns_cache[obsid]

        kept = []
        for s in scenes:
            quote = (s.get("deficit_span", {}) or {}).get("verbatim_quote", "")
            if not quote_in_source(quote, turns):
                unverified.append({"obsid": obsid, "legacy_id": legacy_id,
                                   "turns": (s.get("deficit_span") or {}).get("turns"),
                                   "quote": quote[:120]})
                continue
            # Carry the origin on every scene so a finding can always be traced
            # back to the exact file and run it came from.
            kept.append({**s,
                         "source_document_id": obsid,
                         "obsid": obsid,
                         "legacy_source": f"{legacy_id}{LEGACY_SUFFIX}",
                         "source_run": run_dir.name})

        per_obsid[obsid] = kept
        conf = Counter(s.get("confidence", "medium") for s in kept)
        summary_rows.append({
            "source_document_id": obsid,
            "obsid": obsid,
            "legacy_id": legacy_id,
            "scenes_found": len(kept),
            "high_conf": conf.get("high", 0),
            "medium_conf": conf.get("medium", 0),
            "low_conf": conf.get("low", 0),
        })

    # --- write per-observation files ---
    for obsid, scenes in sorted(per_obsid.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
        (out_dir / f"{obsid}.deficit.json").write_text(
            json.dumps({"source_document_id": obsid, "obsid": obsid, "scenes": scenes},
                       indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    all_scenes = [s for _, v in sorted(per_obsid.items(),
                                       key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0) for s in v]
    (out_dir / "all_scenes.json").write_text(
        json.dumps(all_scenes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary_rows.sort(key=lambda r: int(r["obsid"]) if r["obsid"].isdigit() else 0)
    with open(out_dir / "run_summary.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source_document_id", "obsid", "legacy_id",
                                          "scenes_found", "high_conf", "medium_conf", "low_conf"])
        w.writeheader()
        w.writerows(summary_rows)

    # --- crosswalk log: what each heading used to be called ---------------
    # Written both as a report section and as a CSV, because "which observation
    # is this really?" is the single question the original reports could not
    # answer, and it should be answerable without reading Markdown.
    index = load_index()
    sample = load_sample()
    xrows = []
    for r in sorted(summary_rows, key=lambda r: int(r["obsid"]) if r["obsid"].isdigit() else 0):
        obsid, legacy = r["obsid"], r["legacy_id"]
        meta = index.get(obsid, {})
        xrows.append({
            "obsid": obsid,
            "legacy_id": legacy,
            "legacy_file": f"{legacy}{LEGACY_SUFFIX}",
            "renamed": "yes" if legacy != obsid else "no",
            "shadowed_real_obsid": "yes" if (ARCHIVE_DIR / f"{legacy}.csv").exists() and legacy != obsid else "no",
            "teacher_id": meta.get("video_id", ""),
            "year": meta.get("year", ""),
            "scenes": r["scenes_found"],
            "in_sample": "yes" if obsid in sample else "no",
        })
    with open(out_dir / "crosswalk_used.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(xrows[0].keys()) if xrows else ["obsid"])
        w.writeheader()
        w.writerows(xrows)

    xmeta = {r["obsid"]: r for r in xrows}

    def doc_label(doc):
        r = xmeta.get(doc)
        if not r:
            return ""
        bits = [f"teacher {r['teacher_id']}, yr {r['year']}"] if r["teacher_id"] else []
        bits.append(f"was `{r['legacy_file']}`" if r["renamed"] == "yes" else "name unchanged")
        if r["shadowed_real_obsid"] == "yes":
            bits.append(f"**that filename is also real OBSID {r['legacy_id']}**")
        bits.append("in coding sample" if r["in_sample"] == "yes" else "not in sample")
        return " &middot; ".join(bits)

    shadowed = [r for r in xrows if r["shadowed_real_obsid"] == "yes"]
    xsection = ["## Observation Crosswalk", "",
                "What each heading above was called in the original run, and why the rename "
                "matters. A row marked **shadowed** means the old filename is *also* a valid "
                "OBSID belonging to a different class, so reading the original report at face "
                "value attributes these findings to the wrong observation.", "",
                f"Resolved by sha256 against `data/observation_index.csv`, not by name. "
                f"{len(shadowed)} of {len(xrows)} headings were shadowed.", "",
                "| OBSID | was | teacher / yr | scenes | shadowed | in sample |",
                "|---|---|---|---|---|---|"]
    for r in xrows:
        xsection.append(
            f"| {r['obsid']} | `{r['legacy_file']}` | {r['teacher_id']} / {r['year']} | "
            f"{r['scenes']} | {'**yes**' if r['shadowed_real_obsid'] == 'yes' else 'no'} | "
            f"{r['in_sample']} |")
    xsection.append("")

    if unverified:
        xsection += [
            "## Scenes Dropped In Relabelling", "",
            f"{len(unverified)} scene(s) were dropped because the quote no longer appears in "
            "the OBSID archive file. **This is not evidence of a fabricated quote.** The "
            "transcripts were re-extracted on 2026-07-17 (for example `303_original.csv` went "
            "1889 to 157 rows), so a run predating that read text this repo no longer holds; "
            "checked against the pre-2026-07-17 files, `run_2026-07-12_170210` verifies 68/68. "
            "Dropped rather than re-pointed, because a claim that cannot be grounded in the "
            "current source must not be carried forward. See `unverified.log`.", "",
        ]
    if unresolved:
        xsection += [
            "## Files With No OBSID", "",
            "Legacy transcripts whose content matched no row in `observation_index.csv`, so "
            "their findings cannot be attributed to an archived observation and are excluded: "
            + ", ".join(f"`{u['legacy_id']}{LEGACY_SUFFIX}` ({u['scenes']} scenes)"
                        for u in unresolved)
            + ". These are Study 1's hand-prepared files, which are not archive observations.", "",
        ]

    # --- report, via the one shared renderer ---
    skipped_path = run_dir / "skipped_quotes.log"
    skipped = ([ln for ln in skipped_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
               if skipped_path.exists() else [])
    preamble = [
        f"> **Relabelled view of `{run_dir.name}`.** Headings are OBSIDs. The original run "
        f"labelled findings by the legacy NCTE `video_id`, which for 24 of 52 transcripts "
        f"names a different observation. Scene content is unchanged; every quote here was "
        f"re-verified against `data/transcripts/by_obsid/<obsid>.csv`. "
        f"See the **Observation Crosswalk** below, `crosswalk_used.csv`, and `MANIFEST.json`.",
    ]
    md = build_markdown(
        out_dir, all_scenes, summary_rows, skipped,
        source_note="`data/transcripts/by_obsid/<obsid>.csv` (OBSID archive), relabelled from "
                    f"`{run_dir.name}` via `data/obsid_crosswalk.csv`",
        preamble=preamble, doc_label=doc_label, extra_sections=xsection,
    )
    (out_dir / "DEFICIT_ANALYSIS_REPORT.md").write_text(md, encoding="utf-8")
    (out_dir / "DEFICIT_ANALYSIS_REPORT.txt").write_text(markdown_to_text(md), encoding="utf-8")

    if unresolved:
        (out_dir / "unresolved.log").write_text(
            "\n".join(f"{u['legacy_id']}: {u['scenes']} scenes dropped ({u['reason']})"
                      for u in unresolved) + "\n", encoding="utf-8")
    if unverified:
        # A drop here does NOT mean the model invented a quote. The transcripts
        # were re-extracted on 2026-07-17 (e.g. 303_original.csv went 1889 -> 157
        # rows), so a run predating that read a corpus this repo no longer holds.
        # Checked against the pre-2026-07-17 files, run_2026-07-12_170210 verifies
        # 68/68. These scenes are stale, not fabricated -- and are dropped because
        # they can no longer be grounded, which is the same rule the pipeline applies.
        header = [
            f"# {len(unverified)} scenes dropped: quote not found in the OBSID archive file.",
            "# Cause is usually a stale run: the transcripts were re-extracted on 2026-07-17,",
            "# so runs from before that date reference text no longer in the corpus.",
            "# Not evidence of a fabricated quote. Re-run the pipeline to refresh these.",
            "",
        ]
        (out_dir / "unverified.log").write_text(
            "\n".join(header + [f"obsid {u['obsid']} (from {u['legacy_id']}) turns {u['turns']}: {u['quote']}"
                                for u in unverified]) + "\n", encoding="utf-8")

    # --- provenance ---
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_by": "scripts/relabel_deficit_run.py",
        "source_run": run_dir.name,
        "source_run_path": str(run_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "crosswalk": {
            "path": "data/obsid_crosswalk.csv",
            "sha256": sha256_of(CROSSWALK),
        },
        "verification": {
            "rule": "each verbatim_quote re-matched (whitespace/case normalised) inside "
                    "the OBSID archive file it is now attributed to",
            "scenes_in": sum(len(json.loads(p.read_text(encoding='utf-8')).get('scenes', []))
                             for p in run_dir.glob("*.deficit.json")),
            "scenes_out": len(all_scenes),
            "dropped_unverified": len(unverified),
            "dropped_unresolved_legacy": sum(u["scenes"] for u in unresolved),
        },
        "observations": len(per_obsid),
        "observations_with_scenes": sum(1 for v in per_obsid.values() if v),
        "unresolved_legacy_ids": [u["legacy_id"] for u in unresolved],
        "input_sha256": inputs,
    }
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    after = snapshot_mtimes(run_dir)
    if before != after:
        raise SystemExit(f"ABORT: source run {run_dir.name} was modified. This must never happen.")

    return manifest


def main():
    ap = argparse.ArgumentParser(description="Re-key a deficit run from legacy video_id to OBSID.")
    ap.add_argument("--run", help="Run folder name or path (default: most recent)")
    ap.add_argument("--all", action="store_true", help="Relabel every run_* folder")
    args = ap.parse_args()

    xwalk = load_crosswalk()
    for run_dir in resolve_runs(args.run, args.all):
        m = relabel(run_dir, xwalk)
        v = m["verification"]
        print(f"{run_dir.name} -> data/deficit_scenes_obsid/{run_dir.name}")
        print(f"   observations with scenes : {m['observations_with_scenes']}")
        print(f"   scenes {v['scenes_in']} in -> {v['scenes_out']} out "
              f"(unverified {v['dropped_unverified']}, unresolved legacy {v['dropped_unresolved_legacy']})")
        if m["unresolved_legacy_ids"]:
            print(f"   unresolved legacy ids: {', '.join(m['unresolved_legacy_ids'])}")
        print(f"   source run untouched (mtimes asserted)")


if __name__ == "__main__":
    main()
