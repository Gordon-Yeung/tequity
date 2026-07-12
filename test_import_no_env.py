#!/usr/bin/env python3
"""Test importing anthropic without setting env var."""

print("Step 1: Import anthropic (without setting env var)...")
try:
    import anthropic
    print("  ✓ Import successful!")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\nDone!")
