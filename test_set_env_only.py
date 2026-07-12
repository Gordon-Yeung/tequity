#!/usr/bin/env python3
"""Test just setting env var."""

print("Step 1: Import os...")
import os
print("  Done")

print("Step 2: Set dummy API key...")
os.environ["ANTHROPIC_API_KEY"] = "test-value"
print("  Done")

print("Step 3: Check it's set...")
val = os.environ.get("ANTHROPIC_API_KEY")
print(f"  Value: {val}")

print("Done!")
