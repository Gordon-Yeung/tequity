#!/usr/bin/env python3
print("Starting env test...")

from pathlib import Path

env_file = Path(__file__).parent / ".env"
print(f"Reading from: {env_file}")

try:
    with open(env_file, encoding="utf-8") as f:
        content = f.read()
        print(f"File length: {len(content)} bytes")
        print("First 100 chars:")
        print(repr(content[:100]))
except Exception as e:
    print(f"Error reading file: {e}")
    import traceback
    traceback.print_exc()

print("Env test completed")
