"""
Run all conditions for a video and create a manifest of results.

Usage:
    python scripts/run_all_conditions.py --video_id 706
    python scripts/run_all_conditions.py --video_id 543 --output_dir data/results/
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import subprocess

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


def load_conditions() -> dict:
    path = ROOT / "prompts" / "conditions.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_condition(video_id: str, condition_id: str, output_dir: Path) -> dict:
    """Run a single condition and return metadata about the run."""
    result = {
        "condition_id": condition_id,
        "video_id": video_id,
        "timestamp": datetime.now().isoformat(),
        "status": "unknown",
        "output_file": None,
    }

    # Run the pipeline script
    cmd = [
        sys.executable,
        "scripts/run_condition.py",
        "--video_id", video_id,
        "--condition", condition_id,
        "--save",
        "--output_dir", str(output_dir),
    ]

    try:
        subprocess.run(cmd, check=True, cwd=ROOT)
        result["status"] = "success"
        # The script creates files named: {video_id}_condition{condition_id}_{timestamp}.txt
        # We'll find it by listing the output dir
        files = sorted(output_dir.glob(f"{video_id}_condition{condition_id}_*.txt"))
        if files:
            result["output_file"] = files[-1].name  # most recent
    except subprocess.CalledProcessError as e:
        result["status"] = "failed"
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Run all conditions for a video and create a manifest."
    )
    parser.add_argument("--video_id", required=True, help="Video ID (e.g. 706, 543)")
    parser.add_argument(
        "--output_dir",
        default=str(ROOT / "data" / "results"),
        help="Directory for results (default: data/results/)",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY environment variable is not set.")

    video_id = args.video_id
    output_dir = Path(args.output_dir) / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    conditions = load_conditions()
    manifest = {
        "video_id": video_id,
        "run_timestamp": datetime.now().isoformat(),
        "output_directory": str(output_dir),
        "conditions": [],
    }

    print(f"\n{'=' * 70}")
    print(f"Running all conditions for video {video_id}")
    print(f"Output directory: {output_dir}")
    print(f"{'=' * 70}\n")

    for condition_id in sorted(conditions.keys()):
        cond = conditions[condition_id]
        print(f"\n{'─' * 70}")
        print(f"Running Condition {condition_id}: {cond['name']}")
        print(f"Data source: {cond['input_type']}")
        print(f"{'─' * 70}\n")

        result = run_condition(video_id, condition_id, output_dir)
        result["condition_name"] = cond["name"]
        result["input_type"] = cond["input_type"]
        result["prompt_file"] = cond["prompt_file"]
        manifest["conditions"].append(result)

    # Save manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n{'=' * 70}")
    print(f"Manifest saved to: {manifest_path}")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    import os
    main()
