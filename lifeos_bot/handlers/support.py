from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_bot_edit_message_text, safe_delete_message, safe_edit_message_text, safe_send_message

from lifeos_bot.config import settings
from lifeos_bot.database.db import get_session_maker
from lifeos_bot.services.support_service import SupportService
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.database.models import Subscription
from lifeos_bot.keyboards.main_kb import dashboard_kb
from lifeos_bot.keyboards.support_kb import support_cancel_kb, support_ok_kb
from lifeos_bot.services.dashboard_service import DashboardService
from lifeos_bot.services.quote_service import QuoteService
from lifeos_bot.utils.renderer import render_dashboard

router = Router()


class SupportStates(StatesGroup):
    waiting_text = State()


@router.callback_query(F.data == "nav:support")
async def support_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.message is None:
        await safe_answer_callback(call)
        return

    await state.set_state(SupportStates.waiting_text)

    await state.update_data(prompt_chat_id=call.message.chat.id, prompt_message_id=call.message.message_id)

    await safe_edit_message_text(
        call.message,
        "Опишите проблему или предложение. Сообщение будет отправлено администраторам.",
        reply_markup=support_cancel_kb(),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "support:cancel")
async def support_cancel(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    await state.clear()

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        stats = await DashboardService(session).stats_for_day(user.id, user.selected_date)
        await session.commit()

    data_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
    quote = QuoteService(data_path).get_quote_of_day()
    view = render_dashboard(user.selected_date, quote, dashboard_kb(user.selected_date, tg_user_id=user.tg_user_id), stats)

    await safe_edit_message_text(call.message, view.text, reply_markup=view.keyboard)
    await safe_answer_callback(call)


@router.message(SupportStates.waiting_text)
async def support_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    text = (message.text or "").strip()
    await safe_delete_message(message)

    if not text:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(message.from_user.id)
        await SupportService(session).add_message(user.id, text)
        sub_res = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        sub = sub_res.scalar_one_or_none()
        await session.commit()

    if settings.admin_support_chat_id:
        tg = message.from_user
        username = f"@{tg.username}" if tg.username else "(no username)"
        full_name = " ".join([p for p in [tg.first_name, tg.last_name] if p]) or "(no name)"
        lang = tg.language_code or "(unknown)"

        sub_active = "unknown"
        sub_until = "unknown"
        if isinstance(sub, Subscription):
            sub_active = str(bool(sub.is_active))
            sub_until = sub.active_until.isoformat() if sub.active_until else "-"

        await safe_send_message(
            message.bot,
            chat_id=settings.admin_support_chat_id,
            text=(
                "<b>Support</b>\n"
                f"<b>tg_user_id:</b> {message.from_user.id}\n"
                f"<b>username:</b> {username}\n"
                f"<b>name:</b> {full_name}\n"
                f"<b>lang:</b> {lang}\n\n"
                f"<b>sub_active:</b> {sub_active}\n"
                f"<b>sub_until:</b> {sub_until}\n\n"
                f"<b>message:</b>\n{text}"
            ),
        )

    data = await state.get_data()
    await state.clear()

    chat_id = data.get("prompt_chat_id")
    message_id = data.get("prompt_message_id")
    if chat_id and message_id:
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=chat_id,
            message_id=message_id,
            text="✅ Сообщение отправлено администраторам",
            reply_markup=support_ok_kb(),
        )

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(message.from_user.id)
        stats = await DashboardService(session).stats_for_day(user.id, user.selected_date)
        await session.commit()

    data_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
    quote = QuoteService(data_path).get_quote_of_day()
    view = render_dashboard(user.selected_date, quote, dashboard_kb(user.selected_date, tg_user_id=user.tg_user_id), stats)

    sent = await safe_send_message(message.bot, chat_id=message.chat.id, text=view.text, reply_markup=view.keyboard)
    if sent is None:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        db_user = await users_repo.get_or_create(message.from_user.id)
        await users_repo.set_dashboard_message(db_user.id, sent.chat.id, sent.message_id)
        await session.commit()


@router.callback_query(F.data == "support:ok")
async def support_ok(call: CallbackQuery) -> None:
    if call.message is None:
        await safe_answer_callback(call)
        return

    await safe_delete_message(call.message)
    await safe_answer_callback(call)
