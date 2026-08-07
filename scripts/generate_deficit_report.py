#!/usr/bin/env python3
"""
Deficit-Analysis Report Generator

Renders a human-readable report from a completed deficit_analysis.py run folder.
deficit_analysis.py emits machine-readable artifacts only (JSON + summary CSV);
this script turns those into the DEFICIT_ANALYSIS_REPORT.md / .txt that CLAUDE.md
documents as run outputs.

Read-only with respect to the run's data files: it consumes all_scenes.json and
never rewrites scene records, so a report can be regenerated without touching
the audit trail.

Usage:
    py -3.13 scripts/generate_deficit_report.py                    # newest run
    py -3.13 scripts/generate_deficit_report.py --run run_2026-07-19_153121
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_BASE = REPO_ROOT / "data" / "deficit_scenes"

# Mirrors the A-G taxonomy in prompts/deficit_language_analysis_spec.txt, which
# is the source of truth. Labels here are display-only.
CATEGORY_LABELS = {
    "A": "Fixed-ability framing",
    "B": "Deficit labeling / grouping",
    "C": "Problem located in student/home/background",
    "D": "Deficit attribution for behavior/motivation",
    "E": "Lowered expectations",
    "F": "Comparative deficit",
    "G": "Totalizing negation",
}

CONFIDENCE_ORDER = ["high", "medium", "low"]


def resolve_run_dir(run_arg: str | None) -> Path:
    """Pick the run folder to render: explicit --run, else most recent."""
    if run_arg:
        candidate = Path(run_arg)
        if not candidate.is_absolute():
            candidate = RUNS_BASE / run_arg
        if not candidate.is_dir():
            raise SystemExit(f"Run folder not found: {candidate}")
        return candidate

    runs = sorted(p for p in RUNS_BASE.glob("run_*") if p.is_dir())
    if not runs:
        raise SystemExit(f"No run_* folders under {RUNS_BASE}")
    return runs[-1]


def load_run(run_dir: Path) -> tuple[list[dict], list[dict], list[str]]:
    scenes_path = run_dir / "all_scenes.json"
    if not scenes_path.exists():
        raise SystemExit(f"Missing {scenes_path} - is this a completed run?")
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))

    summary_path = run_dir / "run_summary.csv"
    summary = []
    if summary_path.exists():
        with open(summary_path, newline="", encoding="utf-8") as f:
            summary = list(csv.DictReader(f))

    skipped_path = run_dir / "skipped_quotes.log"
    skipped = []
    if skipped_path.exists():
        skipped = [ln for ln in skipped_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    return scenes, summary, skipped


def source_label(scene: dict) -> str:
    """Strip the _original.csv suffix so tables read as bare video IDs."""
    raw = scene.get("source_document_id", "unknown")
    return raw.replace("_original.csv", "")


DEFAULT_SOURCE_NOTE = "`data/transcripts/*_original.csv` (canonical transcripts; `by_obsid/` excluded)"


def doc_sort_key(doc: str):
    """Numeric where possible. Document ids are OBSIDs in the relabelled report,
    and '1085' sorting before '128' makes a 27-section report unscannable."""
    return (0, int(doc), "") if doc.isdigit() else (1, 0, doc)


def build_markdown(run_dir: Path, scenes: list[dict], summary: list[dict], skipped: list[str],
                   source_note: str = DEFAULT_SOURCE_NOTE, preamble: list[str] | None = None,
                   doc_label=None, extra_sections: list[str] | None = None) -> str:
    """Render a run as Markdown.

    `source_note`, `preamble`, `doc_label` and `extra_sections` exist so the
    OBSID-relabelled view of a run (scripts/relabel_deficit_run.py) reuses this
    one formatter instead of forking it -- the two reports must not drift in
    layout or wording. `doc_label(doc_id)` returns a short descriptor appended
    to each section heading; `extra_sections` are appended at the end.
    """
    total_docs = len(summary) if summary else len({s.get("source_document_id") for s in scenes})
    docs_with = len({s.get("source_document_id") for s in scenes})

    conf_counts = Counter(s.get("confidence", "medium") for s in scenes)
    # A scene may carry several categories; count each membership separately, so
    # these will sum to more than len(scenes).
    cat_counts = Counter(c for s in scenes for c in s.get("categories", []))

    by_doc = defaultdict(list)
    for s in scenes:
        by_doc[source_label(s)].append(s)

    L = []
    L.append("# Deficit-Language Analysis Report")
    L.append("")
    L.append(f"**Run:** `{run_dir.name}`  ")
    L.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    L.append(f"**Source:** {source_note}")
    L.append("")
    L.append("Every quote below was verified verbatim against its source transcript. "
             "Scenes whose quotes did not match exactly were dropped, not corrected.")
    L.append("")
    if preamble:
        L.extend(preamble)
        L.append("")

    L.append("## Overview")
    L.append("")
    L.append("| Metric | Value |")
    L.append("|---|---|")
    L.append(f"| Transcripts processed | {total_docs} |")
    L.append(f"| Transcripts with >=1 scene | {docs_with} |")
    L.append(f"| Transcripts with no scenes | {total_docs - docs_with} |")
    L.append(f"| **Verified scenes** | **{len(scenes)}** |")
    L.append(f"| High confidence | {conf_counts.get('high', 0)} |")
    L.append(f"| Medium confidence | {conf_counts.get('medium', 0)} |")
    L.append(f"| Low confidence | {conf_counts.get('low', 0)} |")
    L.append(f"| Quotes dropped in verification | {len(skipped)} |")
    L.append("")

    L.append("## Category Distribution")
    L.append("")
    L.append("A scene may fall into more than one category, so these sum to more than the scene total.")
    L.append("")
    L.append("| Code | Category | Scenes |")
    L.append("|---|---|---|")
    for code in sorted(CATEGORY_LABELS):
        L.append(f"| {code} | {CATEGORY_LABELS[code]} | {cat_counts.get(code, 0)} |")
    unknown = sorted(set(cat_counts) - set(CATEGORY_LABELS))
    for code in unknown:
        L.append(f"| {code} | *(unrecognized code)* | {cat_counts[code]} |")
    L.append("")

    L.append("## Scenes by Transcript")
    L.append("")
    for doc in sorted(by_doc, key=lambda d: (-len(by_doc[d]), doc_sort_key(d))):
        doc_scenes = by_doc[doc]
        head = f"### {doc} ({len(doc_scenes)} scene{'s' if len(doc_scenes) != 1 else ''})"
        note = doc_label(doc) if doc_label else ""
        L.append(head + (f" &middot; {note}" if note else ""))
        L.append("")
        doc_scenes.sort(key=lambda s: CONFIDENCE_ORDER.index(s.get("confidence", "medium"))
                        if s.get("confidence", "medium") in CONFIDENCE_ORDER else 99)
        for s in doc_scenes:
            span = s.get("deficit_span", {})
            cats = ", ".join(s.get("categories", [])) or "-"
            L.append(f"**Turn {span.get('turns', '?')}** &middot; "
                     f"confidence: `{s.get('confidence', 'medium')}` &middot; "
                     f"categories: {cats}")
            L.append("")
            L.append(f"> {span.get('verbatim_quote', '').strip()}")
            L.append("")
            if s.get("rationale"):
                L.append(f"{s['rationale'].strip()}")
                L.append("")
        L.append("")

    if skipped:
        L.append("## Dropped Quotes")
        L.append("")
        L.append("Flagged by the model but rejected because the quote did not appear verbatim "
                 "in the source. Listed for audit; these are **not** counted as findings.")
        L.append("")
        for ln in skipped:
            L.append(f"- `{ln}`")
        L.append("")

    zero_docs = sorted({r["source_document_id"].replace("_original.csv", "")
                        for r in summary if str(r.get("scenes_found")) == "0"}, key=doc_sort_key)
    if zero_docs:
        L.append("## Transcripts With No Scenes")
        L.append("")
        L.append("Scanned and found clean. These are findings, not gaps.")
        L.append("")
        L.append(", ".join(f"`{d}`" for d in zero_docs))
        L.append("")

    if extra_sections:
        L.extend(extra_sections)

    return "\n".join(L)


def markdown_to_text(md: str) -> str:
    """Flatten the Markdown to plain text for the .txt companion."""
    out = []
    for line in md.splitlines():
        s = line
        if s.startswith("### "):
            s = s[4:]
        elif s.startswith("## "):
            s = s[3:].upper()
        elif s.startswith("# "):
            s = s[2:].upper()
        s = s.replace("**", "").replace("`", "").replace("&middot;", "-")
        s = s.rstrip()
        if s.startswith("> "):
            s = '    "' + s[2:] + '"'
        out.append(s)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Render a deficit-analysis run as MD + TXT.")
    ap.add_argument("--run", help="Run folder name or path (default: most recent)")
    args = ap.parse_args()

    run_dir = resolve_run_dir(args.run)
    scenes, summary, skipped = load_run(run_dir)

    md = build_markdown(run_dir, scenes, summary, skipped)
    md_path = run_dir / "DEFICIT_ANALYSIS_REPORT.md"
    txt_path = run_dir / "DEFICIT_ANALYSIS_REPORT.txt"
    md_path.write_text(md, encoding="utf-8")
    txt_path.write_text(markdown_to_text(md), encoding="utf-8")

    print(f"Run:     {run_dir.name}")
    print(f"Scenes:  {len(scenes)}")
    print(f"Dropped: {len(skipped)}")
    print(f"Wrote:   {md_path}")
    print(f"Wrote:   {txt_path}")


if __name__ == "__main__":
    main()
