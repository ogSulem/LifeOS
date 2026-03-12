from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import Subscription, User


class UsersRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_tg_id(self, tg_user_id: int) -> User | None:
        res = await self.session.execute(select(User).where(User.tg_user_id == tg_user_id))
        return res.scalar_one_or_none()

    async def get_or_create(self, tg_user_id: int, tz: str = "Europe/Moscow") -> User:
        user = await self.get_by_tg_id(tg_user_id)
        if user is not None:
            return user

        user = User(tg_user_id=tg_user_id, tz=tz, selected_date=date.today())
        self.session.add(user)
        await self.session.flush()

        sub = Subscription(user_id=user.id, is_active=False)
        self.session.add(sub)
        await self.session.flush()

        return user

    async def set_dashboard_message(self, user_id: int, chat_id: int, message_id: int) -> None:
        user = await self.session.get(User, user_id)
        if user is None:
            return
        user.dashboard_chat_id = chat_id
        user.dashboard_message_id = message_id

    async def set_selected_date(self, user_id: int, day: date) -> None:
        user = await self.session.get(User, user_id)
        if user is None:
            return
        user.selected_date = day

    async def list_all_tg_user_ids(self) -> list[int]:
        res = await self.session.execute(select(User.tg_user_id))
        return [int(x) for x in res.scalars().all()]
