from __future__ import annotations

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from lifeos_bot.handlers.analytics import router as analytics_router
from lifeos_bot.handlers.admin import router as admin_router
from lifeos_bot.handlers.message_cleanup import router as message_cleanup_router
from lifeos_bot.handlers.goals import router as goals_router
from lifeos_bot.handlers.gratitude import router as gratitude_router
from lifeos_bot.handlers.habits import router as habits_router
from lifeos_bot.handlers.life_goals import router as life_goals_router
from lifeos_bot.handlers.navigation import router as navigation_router
from lifeos_bot.handlers.payments import router as payments_router
from lifeos_bot.handlers.schedule import router as schedule_router
from lifeos_bot.handlers.settings import router as settings_router
from lifeos_bot.handlers.start import router as start_router
from lifeos_bot.handlers.support import router as support_router
from lifeos_bot.handlers.thoughts import router as thoughts_router
from lifeos_bot.handlers.tracking import router as tracking_router
from lifeos_bot.config import settings
from lifeos_bot.middlewares.subscription import SubscriptionMiddleware


def create_dispatcher() -> Dispatcher:
    storage = MemoryStorage()
    if settings.redis_url:
        storage = RedisStorage.from_url(settings.redis_url)

    dp = Dispatcher(storage=storage)

    dp.update.middleware(SubscriptionMiddleware())

    dp.include_router(start_router)
    dp.include_router(thoughts_router)
    dp.include_router(goals_router)
    dp.include_router(life_goals_router)
    dp.include_router(schedule_router)
    dp.include_router(gratitude_router)
    dp.include_router(habits_router)

    dp.include_router(settings_router)

    dp.include_router(analytics_router)
    dp.include_router(support_router)
    dp.include_router(payments_router)
    dp.include_router(tracking_router)

    dp.include_router(admin_router)

    dp.include_router(navigation_router)

    dp.include_router(message_cleanup_router)

    return dp
