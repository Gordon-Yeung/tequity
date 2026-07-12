"""
View and compare results from a condition run.

Usage:
    python scripts/view_results.py --video_id 706
    python scripts/view_results.py --video_id 706 --condition 01
    python scripts/view_results.py --video_id 706 --compare 01 02
"""

import argparse
import json
import os
from pathlib import Path
from tabulate import tabulate

ROOT = Path(__file__).parent.parent

# Load .env file if it exists
env_file = ROOT / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def load_manifest(video_id: str) -> dict:
    """Load the manifest for a video."""
    manifest_path = ROOT / "data" / "results" / video_id / "manifest.json"
    if not manifest_path.exists():
        print(f"No manifest found for video {video_id}")
        print(f"Expected path: {manifest_path}")
        return None
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def view_manifest(video_id: str):
    """Display manifest summary."""
    manifest = load_manifest(video_id)
    if not manifest:
        return

    print(f"\n{'=' * 70}")
    print(f"Results Manifest for Video {video_id}")
    print(f"{'=' * 70}")
    print(f"Run timestamp: {manifest['run_timestamp']}")
    print(f"Output directory: {manifest['output_directory']}\n")

    rows = []
    for cond in manifest["conditions"]:
        rows.append([
            cond["condition_id"],
            cond["condition_name"],
            cond["input_type"],
            cond["status"],
            cond["output_file"] or "N/A",
        ])

    headers = ["ID", "Name", "Data", "Status", "Output File"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print()


def view_condition(video_id: str, condition_id: str):
    """Display output of a specific condition."""
    manifest = load_manifest(video_id)
    if not manifest:
        return

    output_dir = Path(manifest["output_directory"])
    cond_data = next((c for c in manifest["conditions"] if c["condition_id"] == condition_id), None)

    if not cond_data or not cond_data["output_file"]:
        print(f"No output found for condition {condition_id}")
        return

    output_file = output_dir / cond_data["output_file"]
    if not output_file.exists():
        print(f"File not found: {output_file}")
        return

    print(f"\n{'=' * 70}")
    print(f"Video {video_id} | Condition {condition_id}: {cond_data['condition_name']}")
    print(f"Data source: {cond_data['input_type']}")
    print(f"{'=' * 70}\n")

    with open(output_file, encoding="utf-8") as f:
        print(f.read())


def main():
    parser = argparse.ArgumentParser(
        description="View and compare condition results."
    )
    parser.add_argument("--video_id", required=True, help="Video ID (e.g. 706, 543)")
    parser.add_argument("--condition", help="View a specific condition (e.g. 01)")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("COND1", "COND2"),
        help="Compare two conditions side-by-side",
    )
    args = parser.parse_args()

    if args.condition:
        view_condition(args.video_id, args.condition)
    elif args.compare:
        print("Comparison mode not yet implemented")
    else:
        view_manifest(args.video_id)


if __name__ == "__main__":
    main()
