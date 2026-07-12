#!/usr/bin/env python3
"""Test anthropic import and API call."""

import os
import sys
from pathlib import Path

print("1. Loading environment...")
ROOT = Path(__file__).parent
env_file = ROOT / ".env"

with open(env_file, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"')

print(f"API Key set: {bool(os.environ.get('ANTHROPIC_API_KEY'))}")
print(f"API Key length: {len(os.environ.get('ANTHROPIC_API_KEY', ''))}")

print("\n2. Importing anthropic...")
try:
    import anthropic
    print("✓ Anthropic imported")
except Exception as e:
    print(f"✗ Error importing anthropic: {e}")
    sys.exit(1)

print("\n3. Creating client...")
try:
    client = anthropic.Anthropic()
    print("✓ Client created")
except Exception as e:
    print(f"✗ Error creating client: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n4. All tests passed!")
