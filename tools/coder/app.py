#!/usr/bin/env python3
"""
Human deficit-language coding tool (Study 2 companion).

Local Flask app that lets two researchers independently flag teacher turns for
deficit-based language (categories A-G + Other), autosave progress to real JSON
files in the repo, and compare/adjudicate their codings against each other and
against the LLM pipeline output.

Run:
    pip install -r requirements.txt
    python tools/coder/app.py
    # open http://localhost:5000

Design notes:
- Scene-flagging, not full census. Unflagged teacher turns are implicitly "none".
- Turn numbering MUST match scripts/deficit_analysis.py so human flags line up
  with LLM scenes. We reuse its load_transcript (turn_num from enumerate over ALL
  rows, keeping only rows with both speaker and text -> gaps are intentional).
- All paths are repo-relative (deliberately NOT hard-coded like the pipeline).
"""

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import irr

# --- repo-relative paths -----------------------------------------------------
HERE = Path(__file__).resolve().parent            # tools/coder
REPO_ROOT = HERE.parents[1]                        # repo root
TRANSCRIPT_DIR = REPO_ROOT / "data" / "transcripts"
ARCHIVE_DIR = TRANSCRIPT_DIR / "by_obsid"
CODING_DIR = REPO_ROOT / "data" / "human_coding"
DEFICIT_DIR = REPO_ROOT / "data" / "deficit_scenes"
INDEX_PATH = REPO_ROOT / "data" / "observation_index.csv"
SAMPLE_PATH = REPO_ROOT / "data" / "samples" / "one_per_teacher.csv"

CONTEXT_TURNS = 3
CATEGORIES = ["A", "B", "C", "D", "E", "F", "G", "Other"]

# --- reuse canonical loader/verifier from the pipeline -----------------------
# Prefer the single source of truth; fall back to local copies if the pipeline's
# optional deps (anthropic) are unavailable, so the tool stays self-contained.
sys.path.insert(0, str(REPO_ROOT))
try:
    from scripts.deficit_analysis import (  # type: ignore
        load_transcript,
        normalize_text_for_matching,
        find_quote_in_source,
    )
except BaseException:  # noqa: BLE001 - deficit_analysis sys.exit()s if anthropic is absent
    # Fallback: self-contained copies (identical logic) so the tool runs even
    # without the pipeline's optional anthropic dependency.
    import csv

    def load_transcript(filepath):
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            if not rows:
                return [], None

            def nf(name):
                return name.strip().strip('"').strip()

            turns = []
            for idx, row in enumerate(rows, start=1):
                nr = {nf(k): v for k, v in row.items()}
                speaker = (nr.get("speaker") or "").strip()
                text = None
                if "text" in nr:
                    text = (nr["text"] or "").strip()
                elif "cleaned_text" in nr:
                    text = (nr["cleaned_text"] or "").strip()
                if text and speaker:
                    turns.append({"turn_num": idx, "speaker": speaker, "text": text})
            return turns, None
        except Exception as e:
            return [], str(e)

    def normalize_text_for_matching(text):
        return " ".join(text.split()).lower()

    def find_quote_in_source(verbatim_quote, turns):
        nq = normalize_text_for_matching(verbatim_quote)
        return any(nq in normalize_text_for_matching(t["text"]) for t in turns)


app = Flask(__name__, static_folder="static", static_url_path="/static")

# --- helpers -----------------------------------------------------------------
_SAFE = re.compile(r"[^A-Za-z0-9_-]")


def safe_id(value: str) -> str:
    """Filesystem-safe id (coder ids, video ids)."""
    return _SAFE.sub("_", (value or "").strip())[:64]


# --- observation identity ----------------------------------------------------
# The unit of analysis is the OBSID (one observed class). `video_id` in the NCTE
# source is NOT a video: 192 of 319 span more than one year, so it identifies a
# teacher observed repeatedly. Files, coding folders, and URLs are therefore keyed
# on OBSID alone -- one key, one file -- and teacher/year are joined in from
# observation_index.csv for display. Encoding both ids in a filename would be
# ambiguous anyway: OBSID 508 belongs to two teachers.

_index_cache = {"mtime": None, "rows": {}}


def observation_index():
    """obsid -> {teacher_id, year, n_codeable_turns, n_teacher_turns}. Empty if absent."""
    if not INDEX_PATH.exists():
        return {}
    mtime = INDEX_PATH.stat().st_mtime
    if _index_cache["mtime"] != mtime:
        rows = {}
        with open(INDEX_PATH, "r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                rows[r["obsid"]] = {
                    # "732|733" for the one OBSID claimed by two teachers.
                    "teacher_id": r.get("video_id", ""),
                    "year": r.get("year", ""),
                    "n_codeable_turns": int(r.get("n_codeable_turns") or 0),
                    "n_teacher_turns": int(r.get("n_teacher_turns") or 0),
                    "shared_video_id": bool(r.get("shared_video_id")),
                }
        _index_cache.update(mtime=mtime, rows=rows)
    return _index_cache["rows"]


def sampled_obsids():
    """OBSIDs assigned for coding, in manifest order. Empty if no manifest."""
    if not SAMPLE_PATH.exists():
        return []
    with open(SAMPLE_PATH, "r", encoding="utf-8-sig", newline="") as f:
        return [r["obsid"] for r in csv.DictReader(f)]


def coding_targets():
    """The observations this tool works on: the sample manifest, else the legacy
    `*_original.csv` set. Single source of truth so the coding screen and the
    progress dashboard can never disagree about what's in scope."""
    return sampled_obsids() or [
        p.name[: -len("_original.csv")]
        for p in sorted(TRANSCRIPT_DIR.glob("*_original.csv"))
    ]


def transcript_path(obs_id: str):
    """Resolve an id to a transcript file.

    Legacy `<id>_original.csv` wins so the hand-prepared Study 1 files (706, 543)
    and their own column schemas keep working; everything else resolves to the
    OBSID archive.
    """
    legacy = TRANSCRIPT_DIR / f"{safe_id(obs_id)}_original.csv"
    if legacy.exists():
        return legacy
    return ARCHIVE_DIR / f"{safe_id(obs_id)}.csv"


def observation_meta(obs_id: str):
    """Display metadata for an observation; blanks if it predates the index."""
    meta = observation_index().get(obs_id, {})
    return {
        "obsid": obs_id,
        "teacher_id": meta.get("teacher_id", ""),
        "year": meta.get("year", ""),
        "shared_video_id": meta.get("shared_video_id", False),
    }


def load_turns(obs_id: str):
    """Return (turns, error). turns: [{turn_num, speaker, text}]."""
    path = transcript_path(obs_id)
    if not path.exists():
        return [], f"transcript not found: {path.name}"
    return load_transcript(path)


def is_teacher(speaker: str) -> bool:
    return (speaker or "").strip().lower() == "teacher"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def coder_path(obsid: str, coder_id: str):
    return CODING_DIR / safe_id(obsid) / f"{safe_id(coder_id)}.json"


def read_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def context_for(turns, center_turn, window=CONTEXT_TURNS):
    """Return the +/- `window` kept turns around center_turn (index-based, so
    gaps in turn numbering don't drop context)."""
    idx = next((i for i, t in enumerate(turns) if t["turn_num"] == center_turn), None)
    if idx is None:
        return []
    lo = max(0, idx - window)
    hi = min(len(turns), idx + window + 1)
    return [
        {"turn": t["turn_num"], "speaker": t["speaker"], "text": t["text"]}
        for t in turns[lo:hi]
    ]


# --- static ------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# --- transcripts -------------------------------------------------------------
@app.route("/api/transcripts")
def api_transcripts():
    """The observations assigned for coding, with teacher/year joined from the index.

    Driven by the sample manifest so coders see their assignment, not all 1,660
    archived observations. Turn counts come from the index rather than parsing
    every transcript -- at 319 observations that parse was ~8.5MB per page load.
    Falls back to the legacy glob when no manifest exists yet.
    """
    index = observation_index()
    out = []
    for obsid in coding_targets():
        path = transcript_path(obsid)
        meta = index.get(obsid)
        if meta is None:
            # Predates the index (or index not built yet): fall back to parsing.
            turns, err = load_transcript(path) if path.exists() else ([], None)
            counts = {
                "turn_count": len(turns),
                "teacher_turns": sum(1 for t in turns if is_teacher(t["speaker"])),
            }
        else:
            err = None
            counts = {
                "turn_count": meta["n_codeable_turns"],
                "teacher_turns": meta["n_teacher_turns"],
            }
        out.append({
            **observation_meta(obsid),
            **counts,
            # Surfaced at list time so a missing file is visible before a coder
            # picks it, not after they hit Load.
            "error": err or (None if path.exists() else f"transcript not found: {path.name}"),
        })
    return jsonify(out)


@app.route("/api/transcript/<obsid>")
def api_transcript(obsid):
    turns, err = load_turns(obsid)
    if err:
        return jsonify({"error": err}), 404
    return jsonify({
        **observation_meta(obsid),
        "turn_count": len(turns),
        "teacher_turns": sum(1 for t in turns if is_teacher(t["speaker"])),
        "turns": [
            {
                "turn": t["turn_num"],
                "speaker": t["speaker"],
                "text": t["text"],
                "is_teacher": is_teacher(t["speaker"]),
            }
            for t in turns
        ],
    })


# --- coding load/save --------------------------------------------------------
def empty_coding(obsid, coder_id):
    return {
        "obsid": obsid,
        "coder_id": coder_id,
        "created_at": None,
        "updated_at": None,
        "progress": {"last_turn_viewed": 0, "completed": False},
        "scenes": [],
    }


@app.route("/api/coding/<obsid>/<coder_id>", methods=["GET"])
def api_coding_get(obsid, coder_id):
    data = read_json(coder_path(obsid, coder_id))
    if data is None:
        return jsonify(empty_coding(obsid, coder_id))
    return jsonify(data)


@app.route("/api/coding/<obsid>/<coder_id>", methods=["POST"])
def api_coding_save(obsid, coder_id):
    body = request.get_json(force=True, silent=True) or {}
    turns, err = load_turns(obsid)
    if err:
        return jsonify({"error": err}), 404

    turn_text = {t["turn_num"]: t["text"] for t in turns}
    unverified = []
    scenes = []
    for s in body.get("scenes", []):
        turn = s.get("turn")
        # Quote defaults to the full turn text if the coder didn't highlight a span.
        quote = (s.get("verbatim_quote") or "").strip() or turn_text.get(turn, "")
        verified = find_quote_in_source(quote, turns) if quote else False
        if not verified:
            unverified.append(turn)
        scenes.append({
            "scene_id": s.get("scene_id") or f"t{turn}",
            "turn": turn,
            "speaker": s.get("speaker", "teacher"),
            "verbatim_quote": quote,
            "quote_verified": verified,
            "categories": [c for c in s.get("categories", []) if c in CATEGORIES],
            "other_label": (s.get("other_label") or "").strip(),
            "note": (s.get("note") or "").strip(),
            "confidence": s.get("confidence") if s.get("confidence") in ("high", "medium", "low") else "medium",
            "flagged_at": s.get("flagged_at") or now_iso(),
        })

    path = coder_path(obsid, coder_id)
    existing = read_json(path)
    created_at = existing.get("created_at") if existing else None
    data = {
        "obsid": obsid,
        "coder_id": safe_id(coder_id),
        "created_at": created_at or now_iso(),
        "updated_at": now_iso(),
        "progress": body.get("progress", {"last_turn_viewed": 0, "completed": False}),
        "scenes": scenes,
    }
    write_json(path, data)
    return jsonify({"ok": True, "updated_at": data["updated_at"], "unverified": unverified})


# --- status / coders ---------------------------------------------------------
def list_coder_files(obsid):
    d = CODING_DIR / safe_id(obsid)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


@app.route("/api/status")
def api_status():
    """Matrix for the progress dashboard.

    Rows are the in-scope observations, plus any observation that already has
    coding on disk -- so work done before a sample was drawn stays visible
    instead of silently vanishing from the dashboard.
    """
    targets = list(coding_targets())
    coded = sorted(d.name for d in CODING_DIR.glob("*") if d.is_dir() and any(d.glob("*.json")))
    for obsid in coded:
        if obsid not in targets:
            targets.append(obsid)

    out = []
    for obsid in targets:
        coders = []
        for cid in list_coder_files(obsid):
            data = read_json(coder_path(obsid, cid)) or {}
            coders.append({
                "coder_id": cid,
                "scenes": len(data.get("scenes", [])),
                "updated_at": data.get("updated_at"),
                "completed": data.get("progress", {}).get("completed", False),
            })
        out.append({**observation_meta(obsid), "coders": coders})
    return jsonify(out)


@app.route("/api/coders/<obsid>")
def api_coders(obsid):
    return jsonify(list_coder_files(obsid))


# --- LLM import (third coder) ------------------------------------------------
def latest_deficit_file(obsid):
    """Newest run containing this observation.

    Accepts both naming schemes: OBSID-keyed runs over the archive, and the
    legacy `<video_id>_original.deficit.json` from runs that predate the switch.
    """
    if not DEFICIT_DIR.exists():
        return None
    names = (f"{safe_id(obsid)}.deficit.json", f"{safe_id(obsid)}_original.deficit.json")
    runs = sorted((d for d in DEFICIT_DIR.glob("run_*") if d.is_dir()), reverse=True)
    for run in runs:
        for name in names:
            f = run / name
            if f.exists():
                return f
    return None


@app.route("/api/import-llm/<obsid>", methods=["POST"])
def api_import_llm(obsid):
    src = latest_deficit_file(obsid)
    if src is None:
        return jsonify({"error": "no deficit_scenes run found for this transcript"}), 404
    raw = read_json(src)
    scenes = []
    for s in raw.get("scenes", []):
        span = s.get("deficit_span", {})
        turns_field = str(span.get("turns", "")).strip()
        m = re.search(r"\d+", turns_field)
        if not m:
            continue
        turn = int(m.group())
        scenes.append({
            "scene_id": f"t{turn}",
            "turn": turn,
            "speaker": span.get("speaker", "teacher"),
            "verbatim_quote": span.get("verbatim_quote", ""),
            "quote_verified": True,  # pipeline already verified before writing
            "categories": [c for c in s.get("categories", []) if c in CATEGORIES],
            "other_label": "",
            "note": s.get("rationale", ""),
            "confidence": s.get("confidence", "medium"),
            "flagged_at": None,
        })
    data = {
        "obsid": obsid,
        "coder_id": "llm",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "source_run": src.parent.name,
        "progress": {"last_turn_viewed": 0, "completed": True},
        "scenes": scenes,
    }
    write_json(coder_path(obsid, "llm"), data)
    return jsonify({"ok": True, "scenes": len(scenes), "source_run": src.parent.name})


# --- compare -----------------------------------------------------------------
def cats_map(coding):
    """turn -> set(categories) for a coding dict."""
    out = {}
    for s in coding.get("scenes", []):
        out[s["turn"]] = set(s.get("categories", []))
    return out


def scenes_by_turn(coding):
    return {s["turn"]: s for s in coding.get("scenes", [])}


@app.route("/api/compare/<obsid>")
def api_compare(obsid):
    a_id = request.args.get("a")
    b_id = request.args.get("b")
    include_llm = request.args.get("llm") in ("1", "true", "yes")
    if not a_id or not b_id:
        return jsonify({"error": "need ?a= and ?b= coder ids"}), 400

    turns, err = load_turns(obsid)
    if err:
        return jsonify({"error": err}), 404

    a = read_json(coder_path(obsid, a_id)) or empty_coding(obsid, a_id)
    b = read_json(coder_path(obsid, b_id)) or empty_coding(obsid, b_id)
    llm = read_json(coder_path(obsid, "llm")) if include_llm else None

    universe_n = sum(1 for t in turns if is_teacher(t["speaker"]))
    a_turns = set(scenes_by_turn(a))
    b_turns = set(scenes_by_turn(b))

    stats = {
        "universe_teacher_turns": universe_n,
        "binary": irr.binary_agreement(a_turns, b_turns, universe_n),
        "category": irr.category_agreement(cats_map(a), cats_map(b)),
    }

    # LLM-vs-human agreement: same pairwise IRR functions, LLM as the first rater
    # so "a_only" reads as LLM-only. The human-human numbers above are untouched.
    if llm:
        llm_turns = set(scenes_by_turn(llm))
        stats["llm"] = {
            "vs_a": {
                "coder": a_id,
                "binary": irr.binary_agreement(llm_turns, a_turns, universe_n),
                "category": irr.category_agreement(cats_map(llm), cats_map(a)),
            },
            "vs_b": {
                "coder": b_id,
                "binary": irr.binary_agreement(llm_turns, b_turns, universe_n),
                "category": irr.category_agreement(cats_map(llm), cats_map(b)),
            },
        }

    a_sc, b_sc = scenes_by_turn(a), scenes_by_turn(b)
    llm_sc = scenes_by_turn(llm) if llm else {}
    speaker_by_turn = {t["turn_num"]: t["speaker"] for t in turns}
    text_by_turn = {t["turn_num"]: t["text"] for t in turns}

    union = sorted(set(a_sc) | set(b_sc) | set(llm_sc))
    rows = []
    for t in union:
        in_a, in_b = t in a_sc, t in b_sc
        if in_a and in_b:
            status = "agree" if set(a_sc[t]["categories"]) == set(b_sc[t]["categories"]) else "category_mismatch"
        elif in_a:
            status = "a_only"
        else:
            status = "b_only"
        rows.append({
            "turn": t,
            "speaker": speaker_by_turn.get(t, "?"),
            "text": text_by_turn.get(t, ""),
            "context": context_for(turns, t),
            "a": a_sc.get(t),
            "b": b_sc.get(t),
            "llm": llm_sc.get(t),
            "status": status,
        })

    return jsonify({
        "obsid": obsid,
        "a_id": a_id, "b_id": b_id,
        "has_llm": bool(llm),
        "stats": stats,
        "rows": rows,
    })


# --- adjudication ------------------------------------------------------------
@app.route("/api/adjudicated/<obsid>", methods=["GET"])
def api_adjudicated_get(obsid):
    data = read_json(coder_path(obsid, "adjudicated"))
    return jsonify(data or empty_coding(obsid, "adjudicated"))


@app.route("/api/adjudicated/<obsid>", methods=["POST"])
def api_adjudicated_save(obsid):
    body = request.get_json(force=True, silent=True) or {}
    data = {
        "obsid": obsid,
        "coder_id": "adjudicated",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "progress": {"completed": True},
        "scenes": body.get("scenes", []),
    }
    write_json(coder_path(obsid, "adjudicated"), data)
    return jsonify({"ok": True, "scenes": len(data["scenes"])})


if __name__ == "__main__":
    print(f"Serving coder UI at http://localhost:5000  (repo: {REPO_ROOT})")
    app.run(host="127.0.0.1", port=5000, debug=True)
