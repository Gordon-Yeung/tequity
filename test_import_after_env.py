#!/usr/bin/env python3
"""Test importing anthropic after setting env var."""

import os
from pathlib import Path

print("Step 1: Read .env file...")
ROOT = Path(__file__).parent
env_file = ROOT / ".env"

env_vars = {}
with open(env_file, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"')
            env_vars[key] = value
            print(f"  {key}: {value[:30]}...")

print(f"\nStep 2: Set environment variables...")
for key, value in env_vars.items():
    os.environ[key] = value
    print(f"  Set {key}")

print(f"\nStep 3: Verify API key is set...")
api_key = os.environ.get("ANTHROPIC_API_KEY")
print(f"  API Key is set: {bool(api_key)}")
print(f"  API Key length: {len(api_key)}")

print(f"\nStep 4: Import anthropic (this might fail)...")
try:
    import anthropic
    print("  ✓ Import successful!")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\nDone!")
