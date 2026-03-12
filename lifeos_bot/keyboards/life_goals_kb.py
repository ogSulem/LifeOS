from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lifeos_bot.utils.pagination import pager_row


LifeGoalKbItem = tuple[int, bool, int]


def life_categories_kb(
    categories: list[tuple[int, str]],
    page: int = 0,
    total_pages: int = 1,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for cat_id, title in categories:
        rows.append(
            [
                InlineKeyboardButton(text=title, callback_data=f"life:cat:{cat_id}"),
                InlineKeyboardButton(text="🗑", callback_data=f"life:cat_delete:{cat_id}:{page}"),
            ]
        )

    pager = pager_row("life_cats", page, total_pages)
    if pager:
        rows.append(pager)

    rows.append([InlineKeyboardButton(text="➕ Категория", callback_data="life:cat_add")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:dashboard")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def life_category_kb(
    category_id: int,
    goals: list[LifeGoalKbItem],
    page: int = 0,
    total_pages: int = 1,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data=f"life:goal_add:{category_id}")])

    for goal_id, is_done, num in goals:
        mark_emoji = "↩️" if is_done else "✅"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark_emoji} {num}",
                    callback_data=f"life:goal_toggle:{goal_id}:{category_id}:{page}",
                ),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=f"life:goal_delete:{goal_id}:{category_id}:{page}",
                ),
            ]
        )

    pager = pager_row(f"lifegoals:{category_id}", page, total_pages)
    if pager:
        rows.append(pager)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="life:back_to_cats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def life_input_kb(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)]])
