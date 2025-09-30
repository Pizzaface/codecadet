#!/usr/bin/env python3
"""Validate TOML syntax for pyproject_new.toml."""

import tomllib

try:
    with open('pyproject_new.toml', 'rb') as f:
        data = tomllib.load(f)
    print("✅ New TOML syntax is valid")
    print(f"Found {len(data)} top-level sections")
    
    # Check for required sections
    required_sections = ['build-system', 'project', 'tool']
    for section in required_sections:
        if section in data:
            print(f"✅ Found required section: {section}")
        else:
            print(f"❌ Missing required section: {section}")
            
except Exception as e:
    print(f"❌ TOML syntax error: {e}")
