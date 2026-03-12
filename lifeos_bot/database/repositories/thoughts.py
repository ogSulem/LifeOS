from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import Thought


class ThoughtsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_day(self, user_id: int, day: date) -> list[Thought]:
        res = await self.session.execute(
            select(Thought).where(Thought.user_id == user_id, Thought.day == day).order_by(Thought.id.asc())
        )
        return list(res.scalars().all())

    async def add(self, user_id: int, day: date, text: str) -> Thought:
        thought = Thought(user_id=user_id, day=day, text=text)
        self.session.add(thought)
        await self.session.flush()
        return thought

    async def clear_for_day(self, user_id: int, day: date) -> None:
        await self.session.execute(delete(Thought).where(Thought.user_id == user_id, Thought.day == day))
