from __future__ import annotations

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from lifeos_bot.database.repositories.thoughts import ThoughtsRepo
from lifeos_bot.database.models import Thought

class ThoughtsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ThoughtsRepo(session)

    async def get_thoughts_for_day(self, user_id: int, day: date) -> list[Thought]:
        return await self.repo.list_for_day(user_id, day)

    async def add_thought(self, user_id: int, day: date, text: str) -> Thought:
        return await self.repo.add(user_id, day, text)

    async def clear_thoughts(self, user_id: int, day: date) -> None:
        await self.repo.clear_for_day(user_id, day)
