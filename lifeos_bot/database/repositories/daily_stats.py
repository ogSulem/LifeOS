from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import DailyStat


class DailyStatsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, user_id: int, day: date) -> DailyStat:
        res = await self.session.execute(select(DailyStat).where(DailyStat.user_id == user_id, DailyStat.day == day))
        row = res.scalar_one_or_none()
        if row is not None:
            return row
        row = DailyStat(user_id=user_id, day=day)
        self.session.add(row)
        await self.session.flush()
        return row

    async def set_mood(self, user_id: int, day: date, mood: int) -> None:
        row = await self.get_or_create(user_id, day)
        row.mood = mood

    async def set_day_rating(self, user_id: int, day: date, rating: int) -> None:
        row = await self.get_or_create(user_id, day)
        row.day_rating = rating
