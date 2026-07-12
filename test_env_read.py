#!/usr/bin/env python3
"""Test reading .env file line by line."""

from pathlib import Path

ROOT = Path(__file__).parent
env_file = ROOT / ".env"

print("Reading .env line by line...")
with open(env_file, encoding="utf-8") as f:
    for i, line in enumerate(f):
        print(f"Line {i}: {repr(line[:50])}")

print("\nNow trying to parse...")
with open(env_file, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            print(f"Processing: {repr(line[:50])}")
            if "=" in line:
                key, value = line.split("=", 1)
                print(f"  Key: {repr(key)}")
                print(f"  Value: {repr(value[:50])}")

print("Done!")
