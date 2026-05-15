#!/usr/bin/env sh
set -eu

PYTHONPATH="${PYTHONPATH:-src}" python -m foldmind_ai_core.workers.outbox_worker "$@"
