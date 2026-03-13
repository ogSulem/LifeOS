from __future__ import annotations

import re
from dataclasses import dataclass

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.settings_kb import settings_input_kb, settings_kb
from lifeos_bot.services.settings_service import SettingsService
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_bot_edit_message_text, safe_delete_message, safe_edit_message_text


router = Router()


class SettingsStates(StatesGroup):
    waiting_schedule_template = State()
    waiting_habit_template = State()


@dataclass(frozen=True)
class SettingsView:
    text: str


def _render_settings() -> SettingsView:
    return SettingsView(text="<b>⚙️ Настройки</b>")


def _render_schedule_template(items: list[tuple[str | None, str]]) -> SettingsView:
    header = "<b>📅 Шаблон расписания</b>"
    if not items:
        body = "\n\nПока пусто."
    else:
        lines: list[str] = []
        for t, title in items:
            if t:
                lines.append(f"{t} — {title}")
            else:
                lines.append(title)
        body = "\n\n" + "\n".join(lines)
    hint = "\n\nНажмите \"Изменить\", затем отправьте несколько строк."
    return SettingsView(text=header + body + hint)


def _render_habit_template(items: list[str]) -> SettingsView:
    header = "<b>⚡ Шаблон привычек</b>"
    if not items:
        body = "\n\nПока пусто."
    else:
        body = "\n\n" + "\n".join([f"{i + 1}. {t}" for i, t in enumerate(items)])
    hint = "\n\nНажмите \"Изменить\", затем отправьте несколько строк."
    return SettingsView(text=header + body + hint)


_EVENT_RE = re.compile(r"^(?:(?P<time>\d{1,2}:\d{2})\s+)?(?P<title>.+)$")


def _parse_template_event(text: str) -> tuple[str | None, str] | None:
    value = text.strip()
    if not value:
        return None
    m = _EVENT_RE.match(value)
    if not m:
        return None
    title = (m.group("title") or "").strip()
    if not title:
        return None
    time_from = m.group("time")
    if time_from:
        try:
            hh_str, mm_str = time_from.split(":", 1)
            hh = int(hh_str)
            mm = int(mm_str)
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                time_from = f"{hh:02d}:{mm:02d}"
            else:
                time_from = None
        except Exception:
            time_from = None
    return time_from, title


def _parse_multiline(text: str) -> list[str]:
    lines = [x.strip() for x in (text or "").splitlines()]
    return [x for x in lines if x]


async def _load_schedule_template(tg_user_id: int):
    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(tg_user_id)
        service = SettingsService(session)
        items = await service.list_schedule_template(user.id)
        await session.commit()

    view = _render_schedule_template([(x.time_from, x.title) for x in items])
    return view


async def _load_habit_template(tg_user_id: int):
    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(tg_user_id)
        service = SettingsService(session)
        items = await service.list_habit_template(user.id)
        await session.commit()

    view = _render_habit_template([x.title for x in items])
    return view


@router.callback_query(F.data == "nav:settings")
async def open_settings(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()
    view = _render_settings()
    await safe_edit_message_text(call.message, view.text, reply_markup=settings_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data == "settings:schedule")
async def open_schedule_template(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    view = await _load_schedule_template(call.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="settings:schedule:edit")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:settings")],
        ]
    )
    await safe_edit_message_text(call.message, view.text, reply_markup=kb)
    await safe_answer_callback(call)


@router.callback_query(F.data == "settings:habits")
async def open_habit_template(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    view = await _load_habit_template(call.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="settings:habits:edit")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:settings")],
        ]
    )
    await safe_edit_message_text(call.message, view.text, reply_markup=kb)
    await safe_answer_callback(call)


@router.callback_query(F.data == "settings:schedule:edit")
async def schedule_template_edit_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    await state.clear()
    await state.set_state(SettingsStates.waiting_schedule_template)
    await safe_edit_message_text(
        call.message,
        "Отправьте шаблон расписания несколькими строками.\n\nПример:\n`10:00 Тренировка`\n`13:00 Обед`\n`Прогулка`",
        reply_markup=settings_input_kb("settings:schedule"),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "settings:habits:edit")
async def habit_template_edit_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    await state.clear()
    await state.set_state(SettingsStates.waiting_habit_template)
    await safe_edit_message_text(
        call.message,
        "Отправьте шаблон привычек несколькими строками.\n\nПример:\n`Вода 2л`\n`Чтение 20 минут`",
        reply_markup=settings_input_kb("settings:habits"),
    )
    await safe_answer_callback(call)


@router.message(SettingsStates.waiting_schedule_template)
async def schedule_template_edit_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        await state.clear()
        return
    raw = message.text or ""
    await safe_delete_message(message)

    lines = _parse_multiline(raw)
    parsed: list[tuple[str | None, str]] = []
    for line in lines:
        evt = _parse_template_event(line)
        if evt is None:
            continue
        parsed.append(evt)

    if lines and not parsed:
        session_maker = get_session_maker()
        async with session_maker() as session:
            user = await UsersRepo(session).get_or_create(message.from_user.id)
            await session.commit()

        await state.clear()
        if user.dashboard_chat_id and user.dashboard_message_id:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✏️ Изменить", callback_data="settings:schedule:edit")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:settings")],
                ]
            )
            await safe_bot_edit_message_text(
                bot=message.bot,
                chat_id=user.dashboard_chat_id,
                message_id=user.dashboard_message_id,
                text=(
                    "Не удалось распознать шаблон.\n\n"
                    "Формат строк: `10:00 Тренировка` или просто `Тренировка`.\n\n"
                    "Попробуйте ещё раз:"
                ),
                reply_markup=kb,
            )
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(message.from_user.id)
        service = SettingsService(session)
        await service.replace_schedule_template(user.id, parsed)
        await service.apply_templates_for_day(user.id, user.selected_date)
        await session.commit()

    await state.clear()
    view = await _load_schedule_template(message.from_user.id)
    if user.dashboard_chat_id and user.dashboard_message_id:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Изменить", callback_data="settings:schedule:edit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:settings")],
            ]
        )
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=view.text,
            reply_markup=kb,
        )


@router.message(SettingsStates.waiting_habit_template)
async def habit_template_edit_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        await state.clear()
        return
    raw = message.text or ""
    await safe_delete_message(message)

    titles = _parse_multiline(raw)

    if raw.strip() and not titles:
        session_maker = get_session_maker()
        async with session_maker() as session:
            user = await UsersRepo(session).get_or_create(message.from_user.id)
            await session.commit()

        await state.clear()
        if user.dashboard_chat_id and user.dashboard_message_id:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✏️ Изменить", callback_data="settings:habits:edit")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:settings")],
                ]
            )
            await safe_bot_edit_message_text(
                bot=message.bot,
                chat_id=user.dashboard_chat_id,
                message_id=user.dashboard_message_id,
                text="Не удалось распознать ни одной строки.\n\nПопробуйте ещё раз:",
                reply_markup=kb,
            )
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(message.from_user.id)
        service = SettingsService(session)
        await service.replace_habit_template(user.id, titles)
        await service.apply_habit_template(user.id)
        await session.commit()

    await state.clear()
    view = await _load_habit_template(message.from_user.id)
    if user.dashboard_chat_id and user.dashboard_message_id:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Изменить", callback_data="settings:habits:edit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:settings")],
            ]
        )
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=view.text,
            reply_markup=kb,
        )
