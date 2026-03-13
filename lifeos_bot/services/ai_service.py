from __future__ import annotations

import logging
from typing import Any

import httpx

from lifeos_bot.services.analytics_service import AnalyticsSnapshot


class AIService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "openai/gpt-4o-mini",
        enabled: bool = False,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.enabled = enabled

    async def get_coach_recommendation(self, user_id: int, snapshot: AnalyticsSnapshot, timeline: list[dict[str, Any]]) -> str:
        if self.enabled and self.api_key:
            try:
                return await self._openrouter_coach(user_id=user_id, snapshot=snapshot, timeline=timeline)
            except Exception:
                logging.exception("AI coach failed, falling back to heuristic recommendation")

        goals_pct = int((snapshot.goals_done / snapshot.goals_total * 100) if snapshot.goals_total > 0 else 0)
        habits_done = int(snapshot.habits_done)

        trend = ""
        if len(timeline) >= 3:
            first = int(timeline[0].get("goals_pct", 0) or 0)
            last = int(timeline[-1].get("goals_pct", 0) or 0)
            delta = last - first
            if delta >= 15:
                trend = "Тренд по целям: заметный рост."
            elif delta <= -15:
                trend = "Тренд по целям: есть просадка — стоит упростить план."
            else:
                trend = "Тренд по целям: стабильность."

        focus_line = ""
        if snapshot.goals_total == 0:
            focus_line = "Добавь 1 небольшую цель на завтра (10–20 минут) — это даст импульс."
        elif goals_pct < 30:
            focus_line = "На завтра выбери 1 главную цель и 1 простую. Урежь список, чтобы вернуть контроль."
        elif goals_pct < 70:
            focus_line = "Хороший темп. Усиль фокус: выдели 30–45 минут на самую важную цель в первой половине дня."
        else:
            focus_line = "Отлично. Чтобы удержать темп, заранее запланируй отдых и не увеличивай нагрузку резко."

        habits_line = ""
        if snapshot.habits_total == 0:
            habits_line = "Привычки: выбери одну базовую (сон/вода/прогулка) и трекай 7 дней."
        elif habits_done == 0:
            habits_line = "Привычки: начни с минимального шага (сделать 1 раз) — важнее непрерывность."
        else:
            habits_line = "Привычки: закрепляй результат — привяжи выполнение к конкретному триггеру (после/до)."

        parts: list[str] = []
        if trend:
            parts.append(trend)
        parts.append(focus_line)
        parts.append(habits_line)

        return "\n".join(f"- {p}" for p in parts)

    async def _openrouter_coach(
        self,
        user_id: int,
        snapshot: AnalyticsSnapshot,
        timeline: list[dict[str, Any]],
    ) -> str:
        goals_pct = int((snapshot.goals_done / snapshot.goals_total * 100) if snapshot.goals_total > 0 else 0)
        period = (
            f"{snapshot.period_title}: {snapshot.date_from.strftime('%d.%m.%Y')} → {snapshot.date_to.strftime('%d.%m.%Y')}"
        )

        lines: list[str] = [
            f"user_id={user_id}",
            f"period={period}",
            f"goals={snapshot.goals_done}/{snapshot.goals_total} ({goals_pct}%)",
            f"habits_done={snapshot.habits_done} (active={snapshot.habits_total})",
            f"thoughts={snapshot.thoughts}",
            f"gratitude={snapshot.gratitude}",
            f"events={snapshot.events}",
        ]
        if timeline:
            lines.append("timeline:")
            for t in timeline[-14:]:
                lines.append(
                    f"- {t.get('date')}: goals_pct={t.get('goals_pct')}, habits_done={t.get('habits_done')}"
                )

        system = (
            "Ты AI-коуч в Telegram-боте LifeOS. "
            "Дай короткие, конкретные рекомендации на завтра. "
            "Стиль: по делу, без воды. "
            "Формат: 3-5 буллетов, каждый с глаголом действия. "
            "Не используй Markdown-списки с Unicode, используй дефисы '-' в начале строк. "
            "Не упоминай, что ты ИИ и не описывай внутренние расчёты."
        )
        user = "Данные пользователя:\n" + "\n".join(lines)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lifeos.local",
            "X-Title": "LifeOS Assistant",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.6,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content = (
            (data.get("choices") or [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return (content or "").strip() or "- Данных пока мало — добавь 1 цель и 1 привычку на завтра."
