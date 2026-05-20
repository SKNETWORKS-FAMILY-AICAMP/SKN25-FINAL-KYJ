#!/usr/bin/env sh
set -eu

PYTHONPATH="${PYTHONPATH:-src}" python -m foldmind_ai_core.bootstrap.outbox_worker "$@"
