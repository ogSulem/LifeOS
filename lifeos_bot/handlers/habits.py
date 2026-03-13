from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from lifeos_bot.utils.telegram_safe import safe_answer_callback, safe_edit_message_text, safe_bot_edit_message_text, safe_delete_message

from aiogram.types import CallbackQuery, Message

from lifeos_bot.database.db import get_session_maker
from lifeos_bot.services.habit_service import HabitService
from lifeos_bot.database.repositories.users import UsersRepo
from lifeos_bot.keyboards.habits_kb import habits_input_kb, habits_kb

from lifeos_bot.utils.pagination import paginate_by_count

_HABITS_PER_PAGE = 5

router = Router()


class HabitsStates(StatesGroup):
    waiting_title = State()


@dataclass(frozen=True)
class HabitsScreen:
    text: str
    keyboard_data: list[tuple[int, str, bool]]


def _render_habits(day: date, habits: list[tuple[int, str, bool]], *, page: int = 0) -> HabitsScreen:
    header = f"<b>⚡ Привычки</b>\n<b>Дата:</b> {day.strftime('%d.%m.%Y')}"
    if not habits:
        body = "\n\nПока нет привычек. Добавьте первую."
    else:
        max_chars = 3500

        lines_all: list[str] = []
        for i, (_, title, done) in enumerate(habits):
            mark = "✅" if done else "⬜️"
            lines_all.append(f"{i + 1}. {mark} {title}")

        text_all = header + "\n\n" + "\n".join(lines_all)
        if len(text_all) <= max_chars:
            body = "\n\n" + "\n".join(lines_all)
        else:
            sliced = paginate_by_count(habits, page=page, per_page=_HABITS_PER_PAGE)
            start_num = sliced.page * _HABITS_PER_PAGE

            lines_page: list[str] = []
            for i, (_, title, done) in enumerate(sliced.items):
                mark = "✅" if done else "⬜️"
                lines_page.append(f"{start_num + i + 1}. {mark} {title}")
            body = "\n\n" + "\n".join(lines_page)

    return HabitsScreen(text=header + body, keyboard_data=habits)


async def _load_habits(tg_user_id: int) -> tuple[HabitsScreen, int | None, int | None]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(tg_user_id)

        service = HabitService(session)
        habits_data = await service.get_habits_with_logs(user.id, user.selected_date)
        await session.commit()

    return _render_habits(user.selected_date, habits_data), user.dashboard_chat_id, user.dashboard_message_id


async def _load_habits_raw(tg_user_id: int) -> tuple[date, list[tuple[int, str, bool]]]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(tg_user_id)

        service = HabitService(session)
        habits_data = await service.get_habits_with_logs(user.id, user.selected_date)
        await session.commit()

    return user.selected_date, habits_data


@router.callback_query(F.data == "nav:habits")
async def open_habits(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    day, habits_data = await _load_habits_raw(call.from_user.id)
    sliced = paginate_by_count(habits_data, page=0, per_page=_HABITS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        _render_habits(day, habits_data, page=sliced.page).text,
        reply_markup=habits_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("habits:page:"))
async def habits_page(call: CallbackQuery, state: FSMContext) -> None:
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

    day, habits_data = await _load_habits_raw(call.from_user.id)
    sliced = paginate_by_count(habits_data, page=page, per_page=_HABITS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        _render_habits(day, habits_data, page=sliced.page).text,
        reply_markup=habits_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("habits:delete:"))
async def delete_habit(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = call.data.split(":")
    if len(parts) < 3:
        await safe_answer_callback(call)
        return
    habit_id_str = parts[2]
    page = 0
    if len(parts) >= 4:
        try:
            page = int(parts[3])
        except ValueError:
            page = 0
    try:
        habit_id = int(habit_id_str)
    except ValueError:
        await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(call.from_user.id)
        service = HabitService(session)
        habit = await service.get_habit(habit_id)
        if habit is None or int(habit.user_id) != int(user.id) or bool(habit.is_archived):
            await safe_answer_callback(call)
            return
        ok = await service.delete_habit_for_user(user.id, habit_id)
        if not ok:
            await safe_answer_callback(call)
            return
        await session.commit()

    day, habits_data = await _load_habits_raw(call.from_user.id)
    sliced = paginate_by_count(habits_data, page=page, per_page=_HABITS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        _render_habits(day, habits_data, page=sliced.page).text,
        reply_markup=habits_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data.startswith("habits:toggle:"))
async def toggle_habit(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return
    await state.clear()

    parts = call.data.split(":")
    if len(parts) < 3:
        await safe_answer_callback(call)
        return
    habit_id_str = parts[2]
    page = 0
    if len(parts) >= 4:
        try:
            page = int(parts[3])
        except ValueError:
            page = 0
    try:
        habit_id = int(habit_id_str)
    except ValueError:
        await safe_answer_callback(call)
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(call.from_user.id)
        service = HabitService(session)
        habit = await service.get_habit(habit_id)
        if habit is None or int(habit.user_id) != int(user.id) or bool(habit.is_archived):
            await safe_answer_callback(call)
            return
        ok = await service.toggle_habit_for_user(user.id, habit_id, user.selected_date)
        if not ok:
            await safe_answer_callback(call)
            return
        await session.commit()

    day, habits_data = await _load_habits_raw(call.from_user.id)
    sliced = paginate_by_count(habits_data, page=page, per_page=_HABITS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        _render_habits(day, habits_data, page=sliced.page).text,
        reply_markup=habits_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "habits:add")
async def add_habit_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.message is None:
        await safe_answer_callback(call)
        return
    await state.set_state(HabitsStates.waiting_title)
    await safe_edit_message_text(
        call.message,
        "Введите привычки одним сообщением — по одной на строку.\n\nПример:\n`Вода 2л`\n`Чтение 20 минут`\n`Лечь до 23:00`",
        reply_markup=habits_input_kb(),
    )
    await safe_answer_callback(call)


@router.callback_query(F.data == "habits:back")
async def add_habit_back(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if call.from_user is None or call.message is None:
        if call.from_user is not None:
            await safe_answer_callback(call)
        return

    day, habits_data = await _load_habits_raw(call.from_user.id)
    sliced = paginate_by_count(habits_data, page=0, per_page=_HABITS_PER_PAGE)
    await safe_edit_message_text(
        call.message,
        _render_habits(day, habits_data, page=sliced.page).text,
        reply_markup=habits_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
    )
    await safe_answer_callback(call)


@router.message(HabitsStates.waiting_title)
async def add_habit_finish(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    raw = message.text or ""
    await safe_delete_message(message)

    titles = [x.strip() for x in raw.splitlines()]
    titles = [x for x in titles if x]
    if not titles:
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        users_repo = UsersRepo(session)
        user = await users_repo.get_or_create(message.from_user.id)
        service = HabitService(session)
        for title in titles:
            await service.add_habit(user.id, title)
        await session.commit()

    await state.clear()

    view, chat_id, message_id = await _load_habits(message.from_user.id)
    if chat_id and message_id:
        sliced = paginate_by_count(view.keyboard_data, page=0, per_page=_HABITS_PER_PAGE)
        await safe_bot_edit_message_text(
            bot=message.bot,
            chat_id=chat_id,
            message_id=message_id,
            text=view.text,
            reply_markup=habits_kb(sliced.items, page=sliced.page, total_pages=sliced.total_pages),
        )
