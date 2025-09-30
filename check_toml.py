#!/usr/bin/env python3
"""Simple script to validate TOML syntax."""

import tomllib

try:
    with open('pyproject.toml', 'rb') as f:
        data = tomllib.load(f)
    print("✅ TOML syntax is valid")
    print(f"Found {len(data)} top-level sections")
except Exception as e:
    print(f"❌ TOML syntax error: {e}")
