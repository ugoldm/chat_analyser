# Python Pipeline

Автономный пайплайн на Python без `n8n`.

## Что делает

1. Инкрементально догружает новые сообщения из Telegram-чата
2. Считает темы, боли, активность и тренды относительно базового периода
3. Готовит payload для LLM
4. Генерирует HTML-отчёт

## Основные файлы

- `telegram_fetch.py` — забирает новые сообщения и обновляет `state/<chat>.json`
- `aggregate_messages.py` — строит локальную аналитику и `latest_llm_input.json`
- `llm_client.py` — optional OpenAI-compatible клиент
- `render_report.py` — рендерит HTML-отчёт
- `run_daily.py` — orchestrator полного daily run

## Требуемые переменные окружения

- `TG_API_ID`
- `TG_API_HASH`
- `DEFAULT_CHAT` optional
- `FETCH_LIMIT` optional
- `LLM_API_KEY` optional
- `LLM_MODEL` optional
- `LLM_BASE_URL` optional

## Быстрый запуск без LLM

```bash
cd "/Users/ugoldm/Documents/Cursor projects/chat_analyser/python_pipeline"
TG_API_ID=... TG_API_HASH=... python3 run_daily.py --chat selfworkchat --skip-llm
```

## Полный запуск с LLM

```bash
cd "/Users/ugoldm/Documents/Cursor projects/chat_analyser/python_pipeline"
TG_API_ID=... TG_API_HASH=... LLM_API_KEY=... LLM_MODEL=... python3 run_daily.py --chat selfworkchat
```

## Где хранятся артефакты

- `output/raw/<chat>/YYYY-MM-DD.json`
- `output/processed/<chat>/latest_analysis.json`
- `output/processed/<chat>/latest_llm_input.json`
- `output/processed/<chat>/latest_llm_output.json`
- `output/reports/<chat>/latest.html`

## Про Telegram-сессию

По умолчанию пайплайн использует Telethon session из корня проекта:

- `../telegram_user.session`

То есть повторно логиниться не нужно, пока эта сессия валидна.
