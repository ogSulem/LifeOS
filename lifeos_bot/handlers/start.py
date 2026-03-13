from __future__ import annotations

from pathlib import Path

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.repositories.subscriptions import SubscriptionsRepo
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.main_kb import dashboard_kb
from lifeos_bot.keyboards.payments_kb import buy_subscription_kb
from lifeos_bot.middlewares.subscription import SUBSCRIPTION_TEXT
from lifeos_bot.services.dashboard_service import DashboardService
from lifeos_bot.services.settings_service import SettingsService
from lifeos_bot.services.quote_service import QuoteService
from lifeos_bot.utils.renderer import render_dashboard
from lifeos_bot.utils.telegram_safe import safe_bot_edit_message_text, safe_delete_message, safe_send_message

router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    if message.from_user is None:
        await safe_delete_message(message)
        return
    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = UsersRepo(session)
        user = await repo.get_or_create(message.from_user.id)
        await SettingsService(session).apply_templates_for_day(user.id, user.selected_date)
        active = await SubscriptionsRepo(session).is_active_by_tg_id(message.from_user.id)
        stats = await DashboardService(session).stats_for_day(user.id, user.selected_date)
        await session.commit()

    if not active:
        text = SUBSCRIPTION_TEXT
        kb = buy_subscription_kb(show_back=False)
    else:
        data_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
        quote = QuoteService(data_path).get_quote_of_day()
        view = render_dashboard(user.selected_date, quote, dashboard_kb(user.selected_date, tg_user_id=user.tg_user_id), stats)
        text = view.text
        kb = view.keyboard

    # Prefer editing existing "main" message if it was already saved
    if user.dashboard_chat_id and user.dashboard_message_id:
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=text,
            reply_markup=kb,
        )
    else:
        sent = await safe_send_message(message.bot, chat_id=message.chat.id, text=text, reply_markup=kb)
        if sent is None:
            await safe_delete_message(message)
            return
        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = UsersRepo(session)
            db_user = await repo.get_by_tg_id(message.from_user.id)
            if db_user:
                await repo.set_dashboard_message(db_user.id, sent.chat.id, sent.message_id)
            await session.commit()

    await safe_delete_message(message)
