from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import SleepLog


class SleepRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, user_id: int, day: date) -> SleepLog:
        res = await self.session.execute(select(SleepLog).where(SleepLog.user_id == user_id, SleepLog.day == day))
        log = res.scalar_one_or_none()
        if log is not None:
            return log
        log = SleepLog(user_id=user_id, day=day)
        self.session.add(log)
        await self.session.flush()
        return log

    async def set_wakeup(self, user_id: int, day: date, dt: datetime) -> None:
        log = await self.get_or_create(user_id, day)
        log.wakeup_at = dt

    async def set_sleep(self, user_id: int, day: date, dt: datetime) -> None:
        log = await self.get_or_create(user_id, day)
        log.sleep_at = dt
