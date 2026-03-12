from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import HabitTemplate


class HabitTemplatesRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: int) -> list[HabitTemplate]:
        res = await self.session.execute(
            select(HabitTemplate)
            .where(HabitTemplate.user_id == user_id)
            .order_by(HabitTemplate.id.asc())
        )
        return list(res.scalars().all())

    async def replace_all(self, user_id: int, titles: list[str]) -> None:
        await self.session.execute(delete(HabitTemplate).where(HabitTemplate.user_id == user_id))
        for title in titles:
            self.session.add(HabitTemplate(user_id=user_id, title=title))
        await self.session.flush()
