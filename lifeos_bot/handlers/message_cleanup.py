from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from lifeos_bot.utils.telegram_safe import safe_delete_message

router = Router()


@router.message()
async def cleanup_unexpected_messages(message: Message, state=None) -> None:
    text = (message.text or "").strip()
    if text.startswith("/start"):
        return

    if state is not None:
        try:
            st = await state.get_state()
        except Exception:
            st = None
        if st:
            return

    await safe_delete_message(message)
