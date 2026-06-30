#!/bin/bash
cd /c/Users/HP/aevix/backend
uv venv .venv 2>&1
source .venv/Scripts/activate
uv pip install -e ".[dev]" 2>&1 | tail -30
