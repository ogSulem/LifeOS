from __future__ import annotations

from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from lifeos_bot.database.repositories.sleep import SleepRepo
from lifeos_bot.database.repositories.daily_stats import DailyStatsRepo

class TrackingService:
    def __init__(self, session: AsyncSession) -> None:
        self.sleep_repo = SleepRepo(session)
        self.stats_repo = DailyStatsRepo(session)

    async def track_wakeup(self, user_id: int, day: date, dt: datetime) -> None:
        await self.sleep_repo.set_wakeup(user_id, day, dt)

    async def track_sleep(self, user_id: int, day: date, dt: datetime) -> None:
        await self.sleep_repo.set_sleep(user_id, day, dt)

    async def track_mood(self, user_id: int, day: date, mood: int) -> None:
        await self.stats_repo.set_mood(user_id, day, mood)

    async def track_rating(self, user_id: int, day: date, rating: int) -> None:
        await self.stats_repo.set_day_rating(user_id, day, rating)
