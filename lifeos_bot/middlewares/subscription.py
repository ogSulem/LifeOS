from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from lifeos_bot.config import settings
from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.models import Subscription
from lifeos_bot.database.repositories.subscriptions import SubscriptionsRepo
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.payments_kb import buy_subscription_kb
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_bot_edit_message_text, safe_delete_message, safe_edit_message_text, safe_send_message

from sqlalchemy import select


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
        async def _show_subscription_screen_from_message(message: Message | None) -> None:
            if message is not None:
                session_maker = get_session_maker()
                async with session_maker() as session:
                    users_repo = UsersRepo(session)
                    db_user = await users_repo.get_or_create(user.id)
                    sub_res = await session.execute(select(Subscription).where(Subscription.user_id == db_user.id))
                    sub = sub_res.scalar_one_or_none()
                    show_trial = sub is None or sub.trial_used_at is None
                    await session.commit()
                await safe_edit_message_text(
                    message,
                    SUBSCRIPTION_TEXT,
                    reply_markup=buy_subscription_kb(show_back=False, show_trial=show_trial),
                )

        async def _show_subscription_screen_for_user() -> None:
            session_maker = get_session_maker()
            async with session_maker() as session:
                users_repo = UsersRepo(session)
                db_user = await users_repo.get_or_create(user.id)
                chat_id = db_user.dashboard_chat_id
                message_id = db_user.dashboard_message_id
                sub_res = await session.execute(select(Subscription).where(Subscription.user_id == db_user.id))
                sub = sub_res.scalar_one_or_none()
                show_trial = sub is None or sub.trial_used_at is None
                await session.commit()

            if chat_id and message_id:
                await safe_bot_edit_message_text(
                    bot=getattr(event, "bot", None),
                    chat_id=chat_id,
                    message_id=message_id,
                    text=SUBSCRIPTION_TEXT,
                    reply_markup=buy_subscription_kb(show_back=False, show_trial=show_trial),
                )
                return

            chat_id = getattr(getattr(event, "chat", None), "id", None)
            if chat_id is None:
                chat_id = getattr(getattr(getattr(event, "message", None), "chat", None), "id", None)
            if chat_id is None:
                return

            sent = await safe_send_message(
                bot=getattr(event, "bot", None),
                chat_id=chat_id,
                text=SUBSCRIPTION_TEXT,
                reply_markup=buy_subscription_kb(show_back=False, show_trial=show_trial),
            )
            if sent is None:
                return

            session_maker = get_session_maker()
            async with session_maker() as session:
                users_repo = UsersRepo(session)
                db_user = await users_repo.get_or_create(user.id)
                await users_repo.set_dashboard_message(db_user.id, sent.chat.id, sent.message_id)
                await session.commit()

        if isinstance(event, CallbackQuery):
            if event.message:
                await _show_subscription_screen_from_message(event.message)
            else:
                await _show_subscription_screen_for_user()
            await safe_answer_callback(event, "Нужна подписка", show_alert=True)
            return None

        if isinstance(event, Message):
            await safe_delete_message(event)
            await _show_subscription_screen_for_user()
            return None

        return await handler(event, data)
