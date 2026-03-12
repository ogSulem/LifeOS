#!/bin/sh
set -eu

echo "[lifeos] applying migrations..."

# Retry loop: DB may still be initializing even with healthcheck
i=1
while [ "$i" -le 30 ]; do
  if alembic upgrade head; then
    echo "[lifeos] migrations applied"
    break
  fi
  echo "[lifeos] alembic failed, retry $i/30..."
  sleep 2
  if [ "$i" -eq 30 ]; then
    echo "[lifeos] migrations failed after retries"
    exit 1
  fi
  i=$((i+1))
done

echo "[lifeos] starting bot"
exec python -m lifeos_bot.bot.bot
