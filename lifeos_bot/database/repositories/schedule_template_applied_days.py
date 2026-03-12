from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import ScheduleTemplateAppliedDay


class ScheduleTemplateAppliedDaysRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_applied(self, user_id: int, day: date) -> bool:
        res = await self.session.execute(
            select(ScheduleTemplateAppliedDay.id).where(
                ScheduleTemplateAppliedDay.user_id == user_id,
                ScheduleTemplateAppliedDay.day == day,
            )
        )
        return res.scalar_one_or_none() is not None

    async def mark_applied(self, user_id: int, day: date) -> None:
        self.session.add(ScheduleTemplateAppliedDay(user_id=user_id, day=day))
        await self.session.flush()
