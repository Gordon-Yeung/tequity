#!/usr/bin/env python3
print("Script starting...")

try:
    from pathlib import Path
    print(f"Path module imported")

    root = Path(__file__).parent
    print(f"Root: {root}")

    env_file = root / ".env"
    print(f"Checking for: {env_file}")
    print(f"Exists: {env_file.exists()}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("Test completed")
