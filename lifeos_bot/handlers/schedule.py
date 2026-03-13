from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_edit_message_text, safe_bot_edit_message_text, safe_delete_message

from aiogram.types import CallbackQuery, Message

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.services.schedule_service import ScheduleService
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.schedule_kb import schedule_input_kb, schedule_kb

from lifeos_bot.database.models import Event
from lifeos_bot.utils.pagination import paginate_by_count

_SCHEDULE_PER_PAGE = 5

router = Router()


class ScheduleStates(StatesGroup):
    waiting_event_text = State()
    waiting_edit_index = State()
    waiting_edit_text = State()
    waiting_delete_index = State()

    waiting_edit_time = State()
    waiting_edit_title = State()


@dataclass(frozen=True)
class ScheduleScreen:
    text: str


def _render_schedule(
    day: date,
    items: list[tuple[str | None, str | None, str]],
    *,
    page: int,
    per_page: int,
) -> ScheduleScreen:
    header = f"<b>📅 Расписание</b>\n<b>Дата:</b> {day.strftime('%d.%m.%Y')}"
    if not items:
        body = "\n\nПока нет событий."
    else:
        max_chars = 3500

        def _lines(src: list[tuple[str | None, str | None, str]]) -> list[str]:
            lines_out: list[str] = []
            for t_from, t_to, title in src:
                if t_from and t_to:
                    time_part = f"{t_from}-{t_to}"
                elif t_from:
                    time_part = t_from
                else:
                    time_part = ""

                if time_part:
                    lines_out.append(f"{time_part} — {title}")
                else:
                    lines_out.append(title)
            return lines_out

        lines_all = _lines(items)
        hint = "\n\nДля изменения используйте кнопки у события."
        text_all = header + "\n\n" + "\n".join(lines_all) + hint

        if len(text_all) <= max_chars:
            body = "\n\n" + "\n".join(lines_all)
        else:
            start = page * per_page
            end = start + per_page
            lines_page = _lines(items[start:end])
            body = "\n\n" + "\n".join(lines_page)

    hint = "\n\nДля изменения используйте кнопки у события."
    return ScheduleScreen(text=header + body + hint)


async def _load_schedule_screen(tg_user_id: int, page: int) -> tuple[ScheduleScreen, int, int, list[tuple[int, str | None, str | None, str]]]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(tg_user_id)
        events = await ScheduleService(session).get_events_for_day(user.id, user.selected_date)
        await session.commit()

    all_items = [(e.id, e.time_from, e.time_to, e.title) for e in events]
    sliced = paginate_by_count(all_items, page=page, per_page=_SCHEDULE_PER_PAGE)

    view = _render_schedule(
        user.selected_date,
        [(x[1], x[2], x[3]) for x in all_items],
        page=sliced.page,
        per_page=_SCHEDULE_PER_PAGE,
    )
    return view, sliced.page, sliced.total_pages, sliced.items


def _parse_time(text: str) -> str | None:
    value = text.strip()
    if not value:
        return None
    m = re.match(r"^(?P<t>\d{1,2}:\d{2})$", value)
    if not m:
        return None
    return m.group("t")


_TIME_RE = re.compile(
    r"^(?:(?P<from>\d{1,2}:\d{2})(?:-(?P<to>\d{1,2}:\d{2}))?\s+)?(?P<title>.+)$"
)


def _parse_event(text: str) -> tuple[str | None, str | None, str] | None:
    value = text.strip()
    if not value:
        return None
    m = _TIME_RE.match(value)
    if not m:
        return None

    time_from = m.group("from")
    time_to = m.group("to")
    title = (m.group("title") or "").strip()
    if not title:
        return None
    return time_from, time_to, title


def _parse_index(text: str) -> int | None:
    value = text.strip()
    if not value.isdigit():
        return None
    idx = int(value)
    if idx <= 0:
        return None
    return idx


async def _load_schedule(tg_user_id: int) -> tuple[ScheduleScreen, int | None, int | None]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(tg_user_id)
        events = await ScheduleService(session).get_events_for_day(user.id, user.selected_date)
        await session.commit()

    view = _render_schedule(
        user.selected_date,
        [(e.time_from, e.time_to, e.title) for e in events],
        page=0,
        per_page=_SCHEDULE_PER_PAGE,
    )
    return view, user.dashboard_chat_id, user.dashboard_message_id


@router.callback_query(F.data == "nav:schedule")
async def open_schedule(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    view, page, total_pages, events = await _load_schedule_screen(call.from_user.id, page=0)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=schedule_kb(page=page, total_pages=total_pages, events=events),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("schedule:page:"))
async def schedule_page(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    page_str = call.data.split(":", 2)[2]
    try:
        page = int(page_str)
    except ValueError:
        await safe_answer_callback(call)
        return

    view, page, total_pages, events = await _load_schedule_screen(call.from_user.id, page=page)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=schedule_kb(page=page, total_pages=total_pages, events=events),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("schedule:evt_del:"))
async def schedule_evt_delete(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = call.data.split(":")
    if len(parts) < 4:
        await safe_answer_callback(call)
        return
    try:
        event_id = int(parts[2])
        page = int(parts[3])
    except ValueError:
        await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(call.from_user.id)
        ok = await ScheduleService(session).delete_event_for_user(user.id, event_id)
        if not ok:
            await safe_answer_callback(call)
            return
        await session.commit()

    view, page, total_pages, events = await _load_schedule_screen(call.from_user.id, page=page)
    await safe_edit_message_text(
        call.message,
        view.text,
        reply_markup=schedule_kb(page=page, total_pages=total_pages, events=events),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("schedule:evt_time:"))
async def schedule_evt_time_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    parts = call.data.split(":")
    if len(parts) < 4:
        await safe_answer_callback(call)
        return
    try:
        event_id = int(parts[2])
        page = int(parts[3])
    except ValueError:
        await safe_answer_callback(call)
        return

    await state.clear()
    await state.set_state(ScheduleStates.waiting_edit_time)
    await state.update_data(event_id=event_id, page=page)
    await safe_edit_message_text(call.message, "Введите время события (например: `09:00`):", reply_markup=schedule_input_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("schedule:evt_title:"))
async def schedule_evt_title_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    parts = call.data.split(":")
    if len(parts) < 4:
        await safe_answer_callback(call)
        return
    try:
        event_id = int(parts[2])
        page = int(parts[3])
    except ValueError:
        await safe_answer_callback(call)
        return

    await state.clear()
    await state.set_state(ScheduleStates.waiting_edit_title)
    await state.update_data(event_id=event_id, page=page)
    await safe_edit_message_text(call.message, "Введите новое название события (например: `Созвон с командой`):", reply_markup=schedule_input_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data == "schedule:add")
async def schedule_add_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.set_state(ScheduleStates.waiting_event_text)
    await safe_edit_message_text(
        call.message,
        "Введите события одним сообщением — по одному на строку.\n\nПример:\n`09:00-10:00 Встреча`\n`14:00 Обед`\n`Прогулка`",
        reply_markup=schedule_input_kb(),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "schedule:edit")
async def schedule_edit_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.set_state(ScheduleStates.waiting_edit_index)
    await safe_edit_message_text(call.message, "Отправьте номер события для изменения (например: `2`):", reply_markup=schedule_input_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data == "schedule:delete")
async def schedule_delete_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.set_state(ScheduleStates.waiting_delete_index)
    await safe_edit_message_text(call.message, "Отправьте номер события для удаления (например: `3`):", reply_markup=schedule_input_kb())
    await safe_answer_callback(call)


@router.callback_query(F.data == "schedule:back")
async def schedule_back(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    view2, page, total_pages, events = await _load_schedule_screen(call.from_user.id, page=0)
    await safe_edit_message_text(call.message, view2.text, reply_markup=schedule_kb(page=page, total_pages=total_pages, events=events))
    await safe_answer_callback(call)


@router.message(ScheduleStates.waiting_event_text)
async def schedule_add_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    raw = message.text or ""
    await safe_delete_message(message)

    parsed_items: list[tuple[str | None, str | None, str]] = []
    for line in raw.splitlines():
        parsed = _parse_event(line)
        if parsed is None:
            continue
        parsed_items.append(parsed)

    if not parsed_items:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(message.from_user.id)
        service = ScheduleService(session)
        for time_from, time_to, title in parsed_items:
            await service.add_event(
                user.id,
                user.selected_date,
                title=title,
                time_from=time_from,
                time_to=time_to,
            )
        await session.commit()

    await state.clear()
    _, chat_id, message_id = await _load_schedule(message.from_user.id)
    if chat_id and message_id:
        view2, page, total_pages, events = await _load_schedule_screen(message.from_user.id, page=0)
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=chat_id,
            message_id=message_id,
            text=view2.text,
            reply_markup=schedule_kb(page=page, total_pages=total_pages, events=events),
        )


@router.message(ScheduleStates.waiting_edit_index)
async def schedule_edit_index(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    raw = message.text or ""
    await safe_delete_message(message)

    idx = _parse_index(raw)
    if idx is None:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(message.from_user.id)
        events = await ScheduleService(session).get_events_for_day(user.id, user.selected_date)
        await session.commit()

    if idx > len(events):
        return

    await state.set_state(ScheduleStates.waiting_edit_text)
    await state.update_data(event_id=events[idx - 1].id)

    if user.dashboard_chat_id and user.dashboard_message_id:
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text="Введите новое значение события (например: `09:00-10:00 Встреча` или `Прогулка`):",
            reply_markup=schedule_input_kb(),
        )


@router.message(ScheduleStates.waiting_edit_text)
async def schedule_edit_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    raw = message.text or ""
    await safe_delete_message(message)

    parsed = _parse_event(raw)
    if parsed is None:
        return
    time_from, time_to, title = parsed

    data = await state.get_data()
    event_id = data.get("event_id")
    if not isinstance(event_id, int):
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(message.from_user.id)
        ok = await ScheduleService(session).update_event_for_user(
            user.id,
            event_id,
            title=title,
            time_from=time_from,
            time_to=time_to,
        )
        if not ok:
            return
        await session.commit()

    await state.clear()
    _, chat_id, message_id = await _load_schedule(message.from_user.id)
    if chat_id and message_id:
        view2, page, total_pages, events = await _load_schedule_screen(message.from_user.id, page=0)
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=chat_id,
            message_id=message_id,
            text=view2.text,
            reply_markup=schedule_kb(page=page, total_pages=total_pages, events=events),
        )


@router.message(ScheduleStates.waiting_delete_index)
async def schedule_delete_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    raw = message.text or ""
    await safe_delete_message(message)

    idx = _parse_index(raw)
    if idx is None:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(message.from_user.id)
        service = ScheduleService(session)
        events = await service.get_events_for_day(user.id, user.selected_date)
        if idx > len(events):
            return
        await service.delete_event(events[idx - 1].id)
        await session.commit()

    await state.clear()
    _, chat_id, message_id = await _load_schedule(message.from_user.id)
    if chat_id and message_id:
        view2, page, total_pages, events = await _load_schedule_screen(message.from_user.id, page=0)
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=chat_id,
            message_id=message_id,
            text=view2.text,
            reply_markup=schedule_kb(page=page, total_pages=total_pages, events=events),
        )


@router.message(ScheduleStates.waiting_edit_time)
async def schedule_edit_time_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    raw = message.text or ""
    await safe_delete_message(message)

    time_from = _parse_time(raw)
    if time_from is None:
        return
    time_to = None

    data = await state.get_data()
    event_id = data.get("event_id")
    page = data.get("page", 0)
    if not isinstance(event_id, int):
        return
    if not isinstance(page, int):
        page = 0

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(message.from_user.id)
        event = await session.get(Event, event_id)
        if event is None:
            return
        ok = await ScheduleService(session).update_event_for_user(
            user.id,
            event_id,
            title=event.title,
            time_from=time_from,
            time_to=time_to,
        )
        if not ok:
            return
        await session.commit()

    await state.clear()

    view, page, total_pages, events = await _load_schedule_screen(message.from_user.id, page=page)
    if user.dashboard_chat_id and user.dashboard_message_id:
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=view.text,
            reply_markup=schedule_kb(page=page, total_pages=total_pages, events=events),
        )


@router.message(ScheduleStates.waiting_edit_title)
async def schedule_edit_title_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    title = (message.text or "").strip()
    await safe_delete_message(message)
    if not title:
        return

    data = await state.get_data()
    event_id = data.get("event_id")
    page = data.get("page", 0)
    if not isinstance(event_id, int):
        return
    if not isinstance(page, int):
        page = 0

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await UsersRepo(session).get_or_create(message.from_user.id)
        event = await session.get(Event, event_id)
        if event is None:
            return
        ok = await ScheduleService(session).update_event_for_user(
            user.id,
            event_id,
            title=title,
            time_from=event.time_from,
            time_to=event.time_to,
        )
        if not ok:
            return
        await session.commit()

    await state.clear()

    view, page, total_pages, events = await _load_schedule_screen(message.from_user.id, page=page)
    if user.dashboard_chat_id and user.dashboard_message_id:
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=user.dashboard_chat_id,
            message_id=user.dashboard_message_id,
            text=view.text,
            reply_markup=schedule_kb(page=page, total_pages=total_pages, events=events),
        )
