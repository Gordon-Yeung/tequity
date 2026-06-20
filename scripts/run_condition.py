"""
Run a single temporal-prompting condition against a classroom transcript.

Usage:
    python scripts/run_condition.py --video_id 706 --condition 01
    python scripts/run_condition.py --video_id 543 --condition 04 --save
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent


def load_conditions() -> dict:
    path = ROOT / "prompts" / "conditions.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_prompt(prompt_file: str) -> str:
    path = ROOT / prompt_file
    return path.read_text(encoding="utf-8").strip()


def load_transcript(video_id: str) -> str:
    path = ROOT / "data" / "transcripts" / f"{video_id}_original.csv"
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            speaker = row.get("speaker", "").strip()
            text = (row.get("text") or row.get("cleaned_text") or "").strip()
            if speaker and text:
                rows.append(f"{speaker}: {text}")
    return "\n".join(rows)


def load_coded(video_id: str) -> str:
    path = ROOT / "data" / "coded" / f"{video_id}_coded.csv"
    lines = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader)  # skip header row
        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            # Episode header rows have content only in the first cell
            if row[0].strip() and not any(cell.strip() for cell in row[1:]):
                lines.append(f"\n--- {row[0].strip()} ---")
                continue
            speaker = row[0].strip() if len(row) > 0 else ""
            utterance = row[1].strip() if len(row) > 1 else ""
            math_orient = row[2].strip() if len(row) > 2 else ""
            student_orient = row[3].strip() if len(row) > 3 else ""
            interaction_orient = row[4].strip() if len(row) > 4 else ""
            if not speaker and not utterance:
                # researcher commentary between episodes
                commentary = " | ".join(c.strip() for c in row if c.strip())
                if commentary:
                    lines.append(f"[Note: {commentary}]")
                continue
            entry = f"{speaker}: {utterance}"
            if math_orient:
                entry += f"\n  Math orientation: {math_orient}"
            if student_orient:
                entry += f"\n  Student orientation: {student_orient}"
            if interaction_orient:
                entry += f"\n  Interaction orientation: {interaction_orient}"
            lines.append(entry)
    return "\n".join(lines)


def build_message(input_type: str, video_id: str, prompt: str) -> str:
    if input_type == "coded":
        data = load_coded(video_id)
        return f"{data}\n\n{prompt}"
    elif input_type == "transcript":
        data = load_transcript(video_id)
        return f"{data}\n\n{prompt}"
    else:
        raise ValueError(f"Unknown input_type: {input_type!r}")


def run(video_id: str, condition_id: str, save: bool, output_dir: Path) -> str:
    conditions = load_conditions()
    if condition_id not in conditions:
        sys.exit(f"Condition {condition_id!r} not found in conditions.json. "
                 f"Available: {sorted(conditions)}")

    cond = conditions[condition_id]
    print(f"Condition {condition_id}: {cond['name']}")
    print(f"Input type : {cond['input_type']}")
    print(f"Video ID   : {video_id}")
    print("-" * 60)

    prompt_text = load_prompt(cond["prompt_file"])
    message_text = build_message(cond["input_type"], video_id, prompt_text)

    client = anthropic.Anthropic()

    full_response = ""
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": message_text}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text

    print()  # newline after streamed output

    if save:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{video_id}_condition{condition_id}_{timestamp}.txt"
        out_path = output_dir / filename
        out_path.write_text(full_response, encoding="utf-8")
        print(f"\nSaved to: {out_path}")

    return full_response


def main():
    parser = argparse.ArgumentParser(
        description="Run a temporal-prompting condition against a classroom transcript."
    )
    parser.add_argument("--video_id", required=True, help="Video ID (e.g. 706, 543)")
    parser.add_argument("--condition", required=True,
                        help="Condition ID from conditions.json (e.g. 01, 02, 03, 04)")
    parser.add_argument("--save", action="store_true",
                        help="Save the output to a timestamped file")
    parser.add_argument("--output_dir", default=str(ROOT / "data" / "analysis"),
                        help="Directory for saved output files (default: data/analysis/)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY environment variable is not set.")

    run(
        video_id=args.video_id,
        condition_id=args.condition,
        save=args.save,
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
