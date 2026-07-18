#!/usr/bin/env python3
"""
Deficit-Language Analysis Pipeline

Processes classroom transcripts to identify deficit-based language instances.
- Loads all transcript files from input directory
- Uses Claude API to identify deficit-language scenes
- Verifies all quotes against source text
- Generates JSON output, combined file, and run summary
"""

import json
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import unicodedata

try:
    import anthropic
except ImportError:
    print("Error: anthropic package not found. Install with: pip install anthropic")
    sys.exit(1)


def _load_dotenv() -> None:
    """Populate os.environ from a repo-root .env (secrets stay out of git).

    Minimal parser (no python-dotenv dependency): KEY=VALUE lines, ignoring
    blanks/comments and optional surrounding quotes. Existing env vars win.
    """
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# ============================================================================
# CONFIG
# ============================================================================

# Repo-relative paths (scripts/ -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO_ROOT / "data" / "transcripts"
OUTPUT_BASE = REPO_ROOT / "data" / "deficit_scenes"
CONTEXT_TURNS = 3

# Only the canonical single-lesson transcripts are analyzed. This deliberately
# EXCLUDES data/transcripts/by_obsid/ (the per-OBSID audit archive) so a run
# stays scoped to the same 52 files as before the OBSID split.
TRANSCRIPT_GLOB = "*_original.csv"

# ============================================================================
# LOGGING
# ============================================================================

class Logger:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.errors = []
        self.skipped_quotes = []

    def log_error(self, filename: str, error: str):
        msg = f"{filename}: {error}"
        self.errors.append(msg)
        print(f"  ERROR: {msg}")

    def log_skipped_quote(self, filename: str, quote: str, reason: str = ""):
        msg = f"{filename}: {quote[:100]} | {reason}"
        self.skipped_quotes.append(msg)

    def write_logs(self):
        if self.errors:
            with open(self.log_dir / "errors.log", "w", encoding="utf-8") as f:
                f.write("\n".join(self.errors))
        if self.skipped_quotes:
            with open(self.log_dir / "skipped_quotes.log", "w", encoding="utf-8") as f:
                f.write("\n".join(self.skipped_quotes))

# ============================================================================
# TRANSCRIPT LOADING
# ============================================================================

def load_transcript(filepath: Path) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Load transcript from CSV. Handle both formats:
    - Format 1: speaker, text, video_id
    - Format 2: speaker, cleaned_text

    Returns: (list of turn dicts, error message or None)
    Each turn dict has: {turn_num, speaker, text}
    """
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:  # utf-8-sig strips BOM
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return [], None

        # Normalize field names (remove quotes and strip whitespace)
        def normalize_fieldname(name: str) -> str:
            return name.strip().strip('"').strip()

        turns = []
        for idx, row in enumerate(rows, start=1):
            # Create normalized row dict
            normalized_row = {}
            for key, value in row.items():
                normalized_key = normalize_fieldname(key)
                normalized_row[normalized_key] = value

            speaker = normalized_row.get("speaker", "").strip()

            # Determine text column
            text = None
            if "text" in normalized_row:
                text = normalized_row["text"].strip()
            elif "cleaned_text" in normalized_row:
                text = normalized_row["cleaned_text"].strip()

            if text and speaker:
                turns.append({
                    "turn_num": idx,
                    "speaker": speaker,
                    "text": text
                })

        return turns, None
    except Exception as e:
        return [], str(e)

def normalize_text_for_matching(text: str) -> str:
    """Normalize text for fuzzy matching (handle whitespace, case)."""
    # Collapse whitespace, remove extra punctuation variations
    text = " ".join(text.split())
    text = text.lower()
    return text

def find_quote_in_source(verbatim_quote: str, turns: List[Dict[str, Any]]) -> bool:
    """
    Verify that a verbatim quote exists in the source transcript.
    Checks the exact quote against all turn texts.
    """
    normalized_quote = normalize_text_for_matching(verbatim_quote)

    for turn in turns:
        normalized_turn = normalize_text_for_matching(turn["text"])
        if normalized_quote in normalized_turn:
            return True

    return False

# ============================================================================
# DEFICIT ANALYSIS
# ============================================================================

ANALYSIS_SYSTEM_PROMPT = """You are an expert in critical pedagogy and culturally responsive teaching. Your task is to identify instances of deficit-based language in classroom transcripts.

GROUNDING RULES (MANDATORY):
1. Use ONLY the current transcript. Never invent or embellish dialogue.
2. Every quote you report MUST appear verbatim in the source.
3. Report exact turn numbers and source document ID.
4. If a document has no clear deficit instances, return an empty array.
5. Do NOT manufacture examples. A false positive is worse than a miss.
6. Do not flag on a single ambiguous word; context must be clear.

DEFICIT-BASED LANGUAGE CATEGORIES:
A. Fixed-ability framing — ability treated as innate/permanent ("she's just not a math person")
B. Deficit labeling/grouping — students named by lacks ("my low kids", "the ones who can't...")
C. Problem in student/home/background — not in task/instruction ("they come from homes where...")
D. Deficit attribution for behavior/motivation ("they just don't care", "he's lazy")
E. Lowered expectations — cognitive demand reduced justified by perceived inability
F. Comparative deficit — student/class defined by falling short ("not as good as last year's class")
G. Totalizing negation — sweeping "can't/doesn't understand anything" characterizations

WHAT IS NOT DEFICIT-BASED (do not flag):
- Neutral error description ("that answer isn't right, let's check line 3")
- Factual assessment ("about half haven't got the sign yet")
- High-demand questioning ("try it before I help")
- Encouragement or asset-based moves
- Ambiguous cases: prefer NOT flagging; if you do, mark "low" confidence with explanation

RESPONSE FORMAT:
Return a JSON object with structure:
{
  "scenes": [
    {
      "turn_range": "N-M",
      "deficit_span": {
        "speaker": "teacher",
        "turns": "N",
        "verbatim_quote": "<exact text from transcript>"
      },
      "context_turn_numbers": [N-3, N-2, N-1, N, N+1, N+2, N+3],
      "categories": ["A", "B", ...],
      "rationale": "<1-2 sentences explaining which category/why this is deficit>",
      "confidence": "high"|"medium"|"low"
    }
  ]
}

Be conservative. Only flag clear instances. Return empty array if no deficit language found."""

def analyze_transcript_with_claude(turns: List[Dict[str, Any]], video_id: str) -> List[Dict[str, Any]]:
    """
    Use Claude API to analyze transcript for deficit-language instances.
    Returns list of raw scene dicts from Claude.
    """
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    client = anthropic.Anthropic(api_key=api_key)

    # Format transcript for Claude
    transcript_text = "TRANSCRIPT:\n"
    for turn in turns:
        transcript_text += f"Turn {turn['turn_num']} [{turn['speaker']}]: {turn['text']}\n"

    user_prompt = f"""Analyze this classroom transcript (video ID: {video_id}) for deficit-based language.

{transcript_text}

Identify all instances of deficit-based framing. Be conservative—only flag clear cases. Return JSON."""

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        thinking={
            "type": "adaptive"
        },
        system=ANALYSIS_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    # Extract JSON from response
    response_text = response.content[-1].text  # Last block is typically the actual response

    try:
        # Find JSON in response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return data.get("scenes", [])
    except (json.JSONDecodeError, AttributeError):
        pass

    return []

# ============================================================================
# VERIFICATION & OUTPUT
# ============================================================================

def verify_and_filter_scenes(
    scenes: List[Dict[str, Any]],
    turns: List[Dict[str, Any]],
    logger: Logger,
    source_id: str
) -> List[Dict[str, Any]]:
    """
    Verify each scene's verbatim_quote against source turns.
    Drop scenes with unmatched quotes, log them, return verified scenes.
    """
    verified = []

    for scene in scenes:
        if "deficit_span" not in scene or "verbatim_quote" not in scene["deficit_span"]:
            continue

        quote = scene["deficit_span"]["verbatim_quote"]

        if find_quote_in_source(quote, turns):
            verified.append(scene)
        else:
            logger.log_skipped_quote(source_id, quote, "verbatim_quote not found in source")

    return verified

def build_scene_output(
    scene: Dict[str, Any],
    turns: List[Dict[str, Any]],
    source_id: str
) -> Dict[str, Any]:
    """
    Build final scene output with context excerpt.
    Extracts context turns around the deficit utterance.
    """
    # Parse turn range
    turn_range = scene.get("turn_range", "")
    context_turn_nums = scene.get("context_turn_numbers", [])

    # Build context excerpt
    context_excerpt = []
    for turn_num in sorted(set(context_turn_nums)):
        matching_turn = next((t for t in turns if t["turn_num"] == turn_num), None)
        if matching_turn:
            context_excerpt.append({
                "turn": turn_num,
                "speaker": matching_turn["speaker"],
                "text": matching_turn["text"]
            })

    return {
        "turn_range": turn_range,
        "deficit_span": scene.get("deficit_span", {}),
        "context_excerpt": context_excerpt,
        "categories": scene.get("categories", []),
        "rationale": scene.get("rationale", ""),
        "confidence": scene.get("confidence", "medium")
    }

def process_file(
    filepath: Path,
    output_dir: Path,
    logger: Logger,
    input_dir: Path
) -> Tuple[int, Dict[str, int]]:
    """
    Process one transcript file. Return (scenes_count, confidence_counts).
    """
    # Get relative path from input_dir
    try:
        rel_path = filepath.relative_to(input_dir)
        source_id = str(rel_path)
    except ValueError:
        source_id = filepath.name

    print(f"Processing: {source_id}...", end=" ")

    # Load transcript
    turns, load_error = load_transcript(filepath)
    if load_error or not turns:
        error_msg = load_error or "No turns found"
        logger.log_error(source_id, error_msg)
        print(f"FAILED ({error_msg})")
        return 0, {"high": 0, "medium": 0, "low": 0}

    # Analyze with Claude
    try:
        raw_scenes = analyze_transcript_with_claude(turns, source_id.split(os.sep)[0])
    except Exception as e:
        logger.log_error(source_id, f"Claude analysis failed: {str(e)}")
        print(f"FAILED (API error)")
        return 0, {"high": 0, "medium": 0, "low": 0}

    # Verify scenes
    verified_scenes = verify_and_filter_scenes(raw_scenes, turns, logger, source_id)

    # Build final output
    final_scenes = [build_scene_output(scene, turns, source_id) for scene in verified_scenes]

    output_json = {
        "source_document_id": source_id,
        "scenes": final_scenes
    }

    # Write individual JSON file
    output_file = output_dir / f"{filepath.stem}.deficit.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)

    # Count confidence levels
    conf_counts = {"high": 0, "medium": 0, "low": 0}
    for scene in final_scenes:
        conf = scene.get("confidence", "medium")
        if conf in conf_counts:
            conf_counts[conf] += 1

    print(f"OK ({len(final_scenes)} scenes)")
    return len(final_scenes), conf_counts

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("DEFICIT-LANGUAGE ANALYSIS PIPELINE")
    print("=" * 70)

    # Setup output directory with timestamp if needed
    if OUTPUT_BASE.exists():
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_dir = OUTPUT_BASE / f"run_{timestamp}"
    else:
        output_dir = OUTPUT_BASE

    output_dir.mkdir(parents=True, exist_ok=True)
    logger = Logger(output_dir)

    print(f"\nInput directory:  {INPUT_DIR}")
    print(f"Output directory: {output_dir}\n")

    # Enumerate files (top-level canonical transcripts only; NOT recursive, so
    # the by_obsid/ archive is never swept in).
    print("Scanning for transcript files...")
    files = sorted(INPUT_DIR.glob(TRANSCRIPT_GLOB))
    print(f"Found {len(files)} transcript files:\n")
    for f in files:
        try:
            rel = f.relative_to(INPUT_DIR)
        except ValueError:
            rel = f
        print(f"  - {rel}")

    print(f"\nTotal files to process: {len(files)}\n")
    print("=" * 70)
    print("PROCESSING")
    print("=" * 70 + "\n")

    # Process files
    all_scenes = []
    summary_rows = []
    total_files = 0
    total_scenes = 0
    total_dropped = 0

    for filepath in files:
        try:
            rel_path = filepath.relative_to(INPUT_DIR)
            source_id = str(rel_path)
        except ValueError:
            source_id = filepath.name

        scene_count, conf_counts = process_file(filepath, output_dir, logger, INPUT_DIR)
        total_files += 1
        total_scenes += scene_count

        summary_rows.append({
            "source_document_id": source_id,
            "scenes_found": scene_count,
            "high_conf": conf_counts.get("high", 0),
            "medium_conf": conf_counts.get("medium", 0),
            "low_conf": conf_counts.get("low", 0)
        })

        # Collect scenes for all_scenes.json
        scene_file = output_dir / f"{filepath.stem}.deficit.json"
        if scene_file.exists():
            with open(scene_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for scene in data.get("scenes", []):
                    scene["source_document_id"] = source_id
                    all_scenes.append(scene)

    # Write combined scenes file
    with open(output_dir / "all_scenes.json", "w", encoding="utf-8") as f:
        json.dump(all_scenes, f, indent=2, ensure_ascii=False)

    # Write summary CSV
    if summary_rows:
        with open(output_dir / "run_summary.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "source_document_id", "scenes_found", "high_conf", "medium_conf", "low_conf"
            ])
            writer.writeheader()
            writer.writerows(summary_rows)

    # Write logs
    logger.write_logs()

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files processed:     {total_files}")
    print(f"Total scenes found:  {total_scenes}")
    print(f"High confidence:     {sum(r['high_conf'] for r in summary_rows)}")
    print(f"Medium confidence:   {sum(r['medium_conf'] for r in summary_rows)}")
    print(f"Low confidence:      {sum(r['low_conf'] for r in summary_rows)}")
    print(f"Skipped quotes:      {len(logger.skipped_quotes)}")
    print(f"Processing errors:   {len(logger.errors)}")
    print(f"\nOutput files:")
    print(f"  - {len(list(output_dir.glob('*.deficit.json')))} individual scene files")
    print(f"  - all_scenes.json ({len(all_scenes)} total scenes)")
    print(f"  - run_summary.csv")
    if logger.errors:
        print(f"  - errors.log")
    if logger.skipped_quotes:
        print(f"  - skipped_quotes.log")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
