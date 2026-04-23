"""Entry point: python -m glucotrack"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=logging.INFO,
    )

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    from glucotrack.bot.application import create_application
    from glucotrack.config import get_settings
    from glucotrack.db import init_db

    settings = get_settings()

    asyncio.run(init_db(settings.database_url))

    app = create_application(settings)
    logger.info("Starting GlucoTrack bot in polling mode...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
