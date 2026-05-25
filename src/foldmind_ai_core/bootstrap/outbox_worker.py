from __future__ import annotations

import asyncio
import logging

from foldmind_ai_core.bootstrap.container.outbox_worker import OutboxWorkerContainer


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    worker = OutboxWorkerContainer().runtime()
    asyncio.run(worker.run_forever())


if __name__ == "__main__":
    main()
