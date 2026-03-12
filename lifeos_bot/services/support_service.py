from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from lifeos_bot.database.repositories.support import SupportRepo
from lifeos_bot.database.models import SupportMessage

class SupportService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = SupportRepo(session)

    async def add_message(self, user_id: int, text: str) -> SupportMessage:
        return await self.repo.add(user_id, text)
