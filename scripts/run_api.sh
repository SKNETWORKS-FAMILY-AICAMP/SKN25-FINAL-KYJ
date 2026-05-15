#!/usr/bin/env sh
set -eu

PYTHONPATH="${PYTHONPATH:-src}" uvicorn foldmind_ai_core.main:app "$@"
