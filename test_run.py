#!/usr/bin/env python3
"""Test version of run_condition to debug the exit code 5 issue."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent

print(f"ROOT: {ROOT}")
print(f"Script path: {Path(__file__)}")

# Test loading conditions
try:
    import json
    path = ROOT / "prompts" / "conditions.json"
    print(f"Loading from: {path}")
    with open(path, encoding="utf-8") as f:
        conditions = json.load(f)
    print(f"Loaded {len(conditions)} conditions")
except Exception as e:
    print(f"Error loading conditions: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test loading transcript
try:
    import csv
    video_id = "706"
    path = ROOT / "data" / "transcripts" / f"{video_id}_original.csv"
    print(f"Checking transcript at: {path}")
    print(f"Exists: {path.exists()}")
except Exception as e:
    print(f"Error checking transcript: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("All tests passed!")
