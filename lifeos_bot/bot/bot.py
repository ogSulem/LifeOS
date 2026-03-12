from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from lifeos_bot.bot.dispatcher import create_dispatcher
from lifeos_bot.config import settings
from lifeos_bot.database.db import close_db, init_db
from lifeos_bot.utils.scheduler import start_scheduler


def _configure_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    noisy_level = logging.INFO if log_level <= logging.DEBUG else logging.WARNING
    if log_level <= logging.INFO:
        noisy_level = logging.WARNING

    for logger_name in (
        "aiogram",
        "apscheduler",
        "sqlalchemy.engine",
        "httpx",
        "httpcore",
        "asyncio",
    ):
        logging.getLogger(logger_name).setLevel(noisy_level)


async def main() -> None:
    _configure_logging()

    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()

    await start_scheduler(bot)

    try:
        await dp.start_polling(bot)
    finally:
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
