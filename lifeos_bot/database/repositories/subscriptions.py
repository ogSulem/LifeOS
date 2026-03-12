from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import Subscription, User


class SubscriptionsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_active_by_tg_id(self, tg_user_id: int) -> bool:
        res = await self.session.execute(
            select(Subscription)
            .join(User, User.id == Subscription.user_id)
            .where(User.tg_user_id == tg_user_id)
        )
        sub = res.scalar_one_or_none()
        if sub is None:
            return False
        if not sub.is_active:
            return False
        if sub.active_until is None:
            return True
        return sub.active_until >= datetime.utcnow()

    async def activate_by_user_id(self, user_id: int, days: int = 30) -> None:
        sub_res = await self.session.execute(select(Subscription).where(Subscription.user_id == user_id))
        sub = sub_res.scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=user_id)
            self.session.add(sub)
            await self.session.flush()
        sub.is_active = True
        sub.active_until = datetime.utcnow() + timedelta(days=days)
