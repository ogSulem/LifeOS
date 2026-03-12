from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import SupportMessage


class SupportRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user_id: int, text: str) -> SupportMessage:
        msg = SupportMessage(user_id=user_id, text=text)
        self.session.add(msg)
        await self.session.flush()
        return msg
