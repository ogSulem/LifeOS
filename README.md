# LifeOS Assistant

LifeOS Assistant — life-management система в Telegram с UX-подходом **“одно рабочее сообщение”**: почти весь интерфейс живёт в одном сообщении и обновляется через `edit_message_text`, а управление идёт через inline-кнопки.

## Содержание

- [Возможности](#возможности)
- [Быстрый старт (Docker)](#быстрый-старт-docker)
- [Запуск без Docker (локально)](#запуск-без-docker-локально)
- [Переменные окружения](#переменные-окружения)
- [Миграции и база данных](#миграции-и-база-данных)
- [Архитектура](#архитектура)
- [Подписка / оплаты (YooKassa)](#подписка--оплаты-yookassa)
- [Команды для разработки](#команды-для-разработки)
- [Troubleshooting](#troubleshooting)
- [Security](#security)

## Возможности

- **Мысли**: быстрые заметки
- **Благодарности**: список благодарностей на день
- **Цели (ежедневные)**: список с чекбоксами + редактирование/удаление inline
- **Привычки**: трекинг и шаблоны привычек
- **Расписание дня**: события с inline-редактированием времени/названия и удалением
- **Утро/вечер**: регулярные подсказки через APScheduler
- **Аналитика**: день/неделя/месяц, streak
- **Подписка**: paywall и оплата через YooKassa

## Быстрый старт (Docker)

### 0) Подготовь `.env`

Скопируй шаблон и заполни значения:

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Минимум для запуска:

- `BOT_TOKEN`
- `YOOKASSA_SHOP_ID` (если включены оплаты)
- `YOOKASSA_SECRET_KEY` (если включены оплаты)
- `YOOKASSA_RETURN_URL` (обычно ссылка на бота)

### 1) Запуск

Поднимет Postgres + bot, **автоматически применит миграции Alembic** (через `entrypoint.sh`) и запустит polling:

```bash
docker compose up --build
```

### 2) Логи

```bash
docker compose logs -f bot
docker compose logs -f db
```

## Запуск без Docker (локально)

Тебе понадобится:

- Python **3.11+**
- PostgreSQL

### 1) Установка зависимостей

Проект использует зависимости из `pyproject.toml`.

```bash
python -m pip install -U pip
python -m pip install -e .
```

### 2) Настройка окружения

Создай `.env` по шаблону `.env.example` и выставь `DATABASE_URL` на свою БД.

### 3) Миграции

```bash
alembic upgrade head
```

### 4) Запуск бота

```bash
python -m lifeos_bot.bot.bot
```

## Переменные окружения

Основные параметры (см. `.env.example`):

| Переменная | Обязательна | Описание |
|---|---:|---|
| `ENV` | нет | `dev` / `prod` |
| `LOG_LEVEL` | нет | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `TZ` | нет | Таймзона по умолчанию (например `Europe/Moscow`) |
| `BOT_TOKEN` | да | Токен Telegram бота |
| `DATABASE_URL` | да | SQLAlchemy URL (asyncpg) |
| `ADMIN_ID` | нет | Telegram user id админа |
| `ADMIN_SUPPORT_CHAT_ID` | нет | Чат/канал поддержки |
| `PRICE_MONTH` | нет | Цена подписки (руб.) |
| `YOOKASSA_SHOP_ID` | зависит | Shop ID YooKassa |
| `YOOKASSA_SECRET_KEY` | зависит | Secret key YooKassa |
| `YOOKASSA_RETURN_URL` | нет | URL возврата после оплаты |
| `OPENROUTER_ENABLED` | нет | Включить AI-провайдера |
| `OPENROUTER_MODEL` | нет | Модель |
| `OPENROUTER_API_KEY` | зависит | API ключ |

## Миграции и база данных

- Alembic конфиг: `alembic.ini`
- Миграции: `alembic/versions/`
- Docker-режим: миграции применяются автоматически при старте контейнера бота (`entrypoint.sh`).

Полезные команды:

```bash
alembic revision --autogenerate -m "your message"
alembic upgrade head
alembic downgrade -1
```

## Архитектура

Ключевой принцип: **handlers — тонкие**, бизнес-логика — в **services**, доступ к БД — через **repositories**.

- `lifeos_bot/bot/`:
  - запуск, создание `Dispatcher`, polling
  - настройка логирования
- `lifeos_bot/handlers/`:
  - “экраны” (thoughts/goals/schedule/…)
  - FSM состояния для ввода
- `lifeos_bot/services/`:
  - прикладная логика (dashboard/analytics/payment/settings/…)
- `lifeos_bot/database/`:
  - модели SQLAlchemy
  - repositories
  - инициализация сессии
- `lifeos_bot/keyboards/`:
  - inline-клавиатуры
- `lifeos_bot/utils/`:
  - safe-обёртки Telegram API (`safe_edit_message_text`, …)
  - scheduler (APScheduler)
  - общие утилиты

## Подписка / оплаты (YooKassa)

Текущий production-friendly MVP сценарий:

1. Пользователь жмёт `💳 Купить подписку`
2. Бот создаёт платёж в YooKassa
3. Бот показывает:
   - кнопку `💳 Оплатить` (redirect URL)
   - кнопку `✅ Проверить оплату` (fallback)
4. После успешной оплаты:
   - подписка активируется
   - dashboard перерисовывается

Почему есть кнопка `✅ Проверить оплату`:

- для запуска “с нуля” без домена/https/webhook
- как резервный сценарий (если webhook позже добавим и он временно не дошёл)

## Команды для разработки

Ruff (линтер):

```bash
ruff check .
```

Mypy:

```bash
mypy .
```

Сборка и запуск Docker:

```bash
docker compose up --build
```

## Troubleshooting

### Бот не стартует

- Проверь `.env` (особенно `BOT_TOKEN` и `DATABASE_URL`)
- Проверь логи: `docker compose logs -f bot`

### Ошибка подключения к БД

- Проверь, что `db` healthy: `docker compose ps`
- Убедись, что `DATABASE_URL` внутри compose указывает на `db` (в `docker-compose.yml` уже настроено)

### Миграции не применяются в Docker

- Посмотри логи `bot` — `entrypoint.sh` пишет попытки и причины падения
- Если БД поднимается дольше обычного, увеличь retry-политику в `entrypoint.sh`

### YooKassa “не настроена”

- Проверь `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY` в `.env`
- Убедись, что `YOOKASSA_RETURN_URL` корректный

## Security

- `.env` содержит секреты и **не должен коммититься**
- `.env.example` — только шаблон
