"""Worker entry point: ``python -m app.worker``."""

from __future__ import annotations

import logging

from app.worker.scheduler import run_scheduler

logger = logging.getLogger("varagh.worker")


def main() -> None:
    """Start the scheduler and block until the process is stopped."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    )
    logger.info("worker starting")
    run_scheduler()


if __name__ == "__main__":
    main()
