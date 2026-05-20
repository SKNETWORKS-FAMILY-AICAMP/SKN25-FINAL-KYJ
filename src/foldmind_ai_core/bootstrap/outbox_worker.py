from __future__ import annotations

import logging

from foldmind_ai_core.bootstrap.container.outbox import build_outbox_worker
from foldmind_ai_core.bootstrap.settings import load_settings


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    worker = build_outbox_worker(settings=settings)
    worker.run_forever()


if __name__ == "__main__":
    main()
