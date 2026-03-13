from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from lifeos_bot.config import settings
from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.repositories.subscriptions import SubscriptionsRepo
from lifeos_bot.keyboards.payments_kb import buy_subscription_kb
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_delete_message, safe_edit_message_text


SUBSCRIPTION_TEXT = (
    "<b>🧠 LifeOS Assistant</b> — твой личный Life-OS в Telegram.\n"
    "Один экран на день, быстрые действия, никакого хаоса.\n\n"
    "<b>Что ты получишь:</b>\n"
    "• 🎯 Цели на день с чекбоксами\n"
    "• 📅 Расписание (события)\n"
    "• 💭 Мысли и быстрые заметки\n"
    "• 🙏 Благодарности\n"
    "• ⚡ Привычки и шаблоны\n"
    "• 📊 Аналитика и стрик\n"
    "• 🌙 Утро/вечер (подъём, настроение, оценка дня, отбой)\n"
    "• 🤖 AI-коуч (если включён)\n\n"
    "Нажми кнопку ниже, чтобы активировать доступ."
)


class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        # Allow payments/support without active subscription
        if isinstance(event, CallbackQuery):
            cb = event.data or ""
            if cb.startswith("pay:") or cb == "nav:payments":
                return await handler(event, data)
            if cb.startswith("support:") or cb == "nav:support":
                return await handler(event, data)
            # Everything else is blocked until subscription is active

        if isinstance(event, Message):
            text = (event.text or "").strip()
            if text.startswith("/start"):
                return await handler(event, data)
            # Allow support FSM message
            state = data.get("state")
            if state is not None:
                try:
                    st = await state.get_state()
                except Exception:
                    st = None
                if st and "SupportStates" in st:
                    return await handler(event, data)

        session_maker = get_session_maker()
        async with session_maker() as session:
            active = await SubscriptionsRepo(session).is_active_by_tg_id(user.id)

        if active:
            return await handler(event, data)

        # Blocked: show subscription screen
        if isinstance(event, CallbackQuery):
            if event.message:
                await safe_edit_message_text(
                    event.message,
                    SUBSCRIPTION_TEXT,
                    reply_markup=buy_subscription_kb(show_back=False),
                )
            await safe_answer_callback(event, "Нужна подписка", show_alert=True)
            return None

        if isinstance(event, Message):
            await safe_delete_message(event)
            return None

        return await handler(event, data)
