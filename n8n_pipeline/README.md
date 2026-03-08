# n8n Pipeline

Эта папка содержит код и инструкции для сборки пайплайна полностью внутри `n8n`:

1. `Schedule Trigger`
2. `Python Code` node: `fetch_messages_node.py`
3. `Python Code` node: `aggregate_messages_node.py`
4. `LLM` node
5. `Python Code` node: `render_html_node.py`

## Хранение состояния

- `last_message_id` — в `workflow static data` или `Data Store`
- сырые батчи сообщений — в `Data Store`
- HTML-отчёты — в `Data Store`, Google Drive, Notion или email

## Секреты

Сохраняйте в `n8n`:

- `TG_API_ID`
- `TG_API_HASH`
- `TG_STRING_SESSION`
- `TG_CHAT`

## Что лежит в папке

- `fetch_messages_node.py` — код первой Python node для Telegram fetch
- `aggregate_messages_node.py` — код ноды локальной аналитики и подготовки LLM input
- `render_html_node.py` — код HTML renderer node
