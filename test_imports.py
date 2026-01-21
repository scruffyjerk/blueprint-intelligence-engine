#!/usr/bin/env python3
"""Test that all imports work correctly."""

import sys
sys.path.insert(0, 'src')

try:
    from api.main import app
    print("Imports successful!")
except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
