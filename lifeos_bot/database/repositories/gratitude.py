from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import Gratitude


class GratitudeRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_day(self, user_id: int, day: date) -> list[Gratitude]:
        res = await self.session.execute(
            select(Gratitude)
            .where(Gratitude.user_id == user_id, Gratitude.day == day)
            .order_by(Gratitude.id.asc())
        )
        return list(res.scalars().all())

    async def add(self, user_id: int, day: date, text: str) -> Gratitude:
        item = Gratitude(user_id=user_id, day=day, text=text)
        self.session.add(item)
        await self.session.flush()
        return item

    async def clear_for_day(self, user_id: int, day: date) -> None:
        await self.session.execute(delete(Gratitude).where(Gratitude.user_id == user_id, Gratitude.day == day))
