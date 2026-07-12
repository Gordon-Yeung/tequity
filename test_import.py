#!/usr/bin/env python3
import sys
import os

# Load .env
env_file = "C:/Users/Gordon Yeung/Documents/GitHub/temporal-prompting/.env"
with open(env_file) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"')

print("Environment loaded")
print(f"API Key set: {bool(os.environ.get('ANTHROPIC_API_KEY'))}")

try:
    import anthropic
    print("Anthropic imported successfully")
except Exception as e:
    print(f"Error importing anthropic: {e}")
    import traceback
    traceback.print_exc()

print("Now trying to import run_condition...")
try:
    from scripts.run_condition import run
    print("run_condition imported successfully")
except Exception as e:
    print(f"Error importing run_condition: {e}")
    import traceback
    traceback.print_exc()
