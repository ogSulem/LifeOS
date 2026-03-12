from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lifeos_bot.database.models import PaymentAttempt


class PaymentsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_attempt(
        self,
        user_id: int,
        provider_payment_id: str,
        amount_rub: int,
        status: str = "pending",
        provider: str = "yookassa",
    ) -> PaymentAttempt:
        attempt = PaymentAttempt(
            user_id=user_id,
            provider=provider,
            provider_payment_id=provider_payment_id,
            amount_rub=amount_rub,
            status=status,
        )
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> PaymentAttempt | None:
        res = await self.session.execute(
            select(PaymentAttempt).where(PaymentAttempt.provider_payment_id == provider_payment_id)
        )
        return res.scalar_one_or_none()

    async def set_status(self, provider_payment_id: str, status: str) -> None:
        attempt = await self.get_by_provider_payment_id(provider_payment_id)
        if attempt is None:
            logging.warning("PaymentAttempt not found for provider_payment_id=%s", provider_payment_id)
            return
        attempt.status = status
