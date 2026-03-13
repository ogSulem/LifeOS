from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from lifeos_bot.config import settings
from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.repositories.subscriptions import SubscriptionsRepo
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.main_kb import dashboard_kb
from lifeos_bot.keyboards.payments_kb import buy_subscription_kb
from lifeos_bot.middlewares.subscription import SUBSCRIPTION_TEXT
from lifeos_bot.services.dashboard_service import DashboardService
from lifeos_bot.services.quote_service import QuoteService
from lifeos_bot.utils.renderer import render_dashboard
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_bot_edit_message_text, safe_delete_message, safe_edit_message_text, safe_send_message

router = Router()


class AdminStates(StatesGroup):
    waiting_broadcast_text = State()


def _is_admin(tg_user_id: int) -> bool:
    return settings.admin_id is not None and tg_user_id == settings.admin_id


def _admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="☀️ Утро", callback_data="admin:test:morning"),
                InlineKeyboardButton(text="🌙 Ночь", callback_data="admin:test:night"),
            ],
            [InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="💳 Подписка (тест)", callback_data="admin:sub:test")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")],
        ]
    )


def _broadcast_done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="ОК", callback_data="admin:broadcast:ok")]]
    )


@router.callback_query(F.data == "admin:panel")
async def admin_panel_open(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    if not _is_admin(call.from_user.id):
        await safe_answer_callback(call)
        return

    await state.clear()
    await safe_edit_message_text(call.message, "<b>🛠 Админ-панель</b>", reply_markup=_admin_panel_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    if not _is_admin(call.from_user.id):
        await safe_answer_callback(call)
        return

    await state.set_state(AdminStates.waiting_broadcast_text)
    await state.update_data(prompt_chat_id=call.message.chat.id, prompt_message_id=call.message.message_id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel")]]
    )
    await safe_edit_message_text(
        call.message,
        "Отправьте текст рассылки одним сообщением:",
        reply_markup=kb,
    )
    await safe_answer_callback(call)


@router.message(AdminStates.waiting_broadcast_text)
async def admin_broadcast_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    if not _is_admin(message.from_user.id):
        await safe_delete_message(message)
        await state.clear()
        return

    if message.text is None:
        await safe_delete_message(message)
        return

    text = message.text.strip()
    await safe_delete_message(message)
    if not text:
        return

    data = await state.get_data()
    await state.clear()

    prompt_chat_id = data.get("prompt_chat_id")
    prompt_message_id = data.get("prompt_message_id")
    if not prompt_chat_id or not prompt_message_id:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        tg_user_ids = await users_repo.list_all_tg_user_ids()
        await session.commit()

    sent_ok = 0
    for tg_user_id in tg_user_ids:
        sent = await safe_send_message(message.bot, chat_id=tg_user_id, text=text)
        if sent is not None:
            sent_ok += 1

    await safe_bot_edit_message_text(
        bot=message.bot,
        chat_id=int(prompt_chat_id),
        message_id=int(prompt_message_id),
        text=f"✅ Сообщение отправлено всем юзерам ({sent_ok}/{len(tg_user_ids)})",
        reply_markup=_broadcast_done_kb(),
    )

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(message.from_user.id)
        stats = await DashboardService(session).stats_for_day(user.id, user.selected_date)
        await session.commit()

    data_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
    quote = QuoteService(data_path).get_quote_of_day()
    view = render_dashboard(user.selected_date, quote, dashboard_kb(user.selected_date, tg_user_id=user.tg_user_id), stats)
    sent = await safe_send_message(message.bot, chat_id=int(prompt_chat_id), text=view.text, reply_markup=view.keyboard)
    if sent is None:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        db_user = await users_repo.get_or_create(message.from_user.id)
        await users_repo.set_dashboard_message(db_user.id, sent.chat.id, sent.message_id)
        await session.commit()


@router.callback_query(F.data == "admin:broadcast:ok")
async def admin_broadcast_ok(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    if not _is_admin(call.from_user.id):
        await safe_answer_callback(call)
        return

    await safe_delete_message(call.message)
    await safe_answer_callback(call)


@router.callback_query(F.data == "admin:sub:test")
async def admin_test_subscription(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    if not _is_admin(call.from_user.id):
        await safe_answer_callback(call)
        return

    await state.clear()

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        await SubscriptionsRepo(session).deactivate_by_user_id(user.id)
        await session.commit()

    await safe_edit_message_text(
        call.message,
        SUBSCRIPTION_TEXT,
        reply_markup=buy_subscription_kb(show_back=False),
    )
    await safe_answer_callback(call)

