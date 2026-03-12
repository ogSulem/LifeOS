from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from yookassa import Configuration, Payment

from lifeos_bot.config import settings


@dataclass(frozen=True)
class CreatedPayment:
    payment_id: str
    confirmation_url: str
    status: str


class PaymentService:
    def __init__(self) -> None:
        if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
            raise RuntimeError("YooKassa is not configured")

        if not settings.yookassa_return_url:
            raise RuntimeError("YOOKASSA_RETURN_URL is not configured")

        Configuration.account_id = settings.yookassa_shop_id
        Configuration.secret_key = settings.yookassa_secret_key

    async def create_subscription_payment(self, amount_rub: int, description: str) -> CreatedPayment:
        # YooKassa SDK is sync, but network I/O is inside the SDK.
        # For simplicity we call it directly; if needed, wrap in asyncio.to_thread.
        def _create():
            payload = {
                "amount": {"value": f"{amount_rub}.00", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": settings.yookassa_return_url,
                },
                "capture": True,
                "description": description,
            }
            return Payment.create(payload, str(uuid4()))

        payment = await asyncio.to_thread(_create)

        return CreatedPayment(
            payment_id=str(payment.id),
            confirmation_url=str(payment.confirmation.confirmation_url),
            status=str(payment.status),
        )

    async def get_payment_status(self, payment_id: str) -> str:
        payment = await asyncio.to_thread(Payment.find_one, payment_id)
        return str(payment.status)
