import argparse
import asyncio
import json
import os
from datetime import timezone
from pathlib import Path

from telethon import TelegramClient

from pipeline.analysis_core import ensure_directory, load_json, save_json, slugify_chat, utc_now


ROOT = Path(__file__).resolve().parents[1]
SESSION_BASE = ROOT / "telegram_user"
OUTPUT_ROOT = Path(__file__).with_name("output") / "raw"
STATE_DIR = Path(__file__).with_name("state")


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incrementally fetch Telegram messages.")
    parser.add_argument("--chat", required=True, help="Chat username or link.")
    parser.add_argument("--limit", type=int, default=5000, help="Maximum new messages to fetch.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    api_id = int(require_env("TG_API_ID"))
    api_hash = require_env("TG_API_HASH")

    chat_slug = slugify_chat(args.chat)
    state_path = STATE_DIR / f"{chat_slug}.json"
    state = load_json(state_path, default={})
    last_message_id = int(state.get("last_message_id", 0))

    client = TelegramClient(str(SESSION_BASE), api_id, api_hash)
    async with client:
        entity = await client.get_entity(args.chat)
        title = getattr(entity, "title", None) or getattr(entity, "username", None) or args.chat
        chat_id = getattr(entity, "id", None)

        if last_message_id > 0:
            iterator = client.iter_messages(entity, min_id=last_message_id, reverse=True, limit=args.limit)
        else:
            iterator = client.iter_messages(entity, limit=args.limit)

        messages = []
        async for message in iterator:
            sender = message.sender
            sender_name = None
            sender_is_bot = False
            if sender is not None:
                first = getattr(sender, "first_name", "") or ""
                last = getattr(sender, "last_name", "") or ""
                username = getattr(sender, "username", "") or ""
                sender_is_bot = bool(getattr(sender, "bot", False))
                sender_name = " ".join(part for part in [first, last] if part).strip() or (f"@{username}" if username else None)

            messages.append(
                {
                    "id": message.id,
                    "date": message.date.astimezone(timezone.utc).isoformat() if message.date else None,
                    "sender_id": message.sender_id or 0,
                    "sender_name": sender_name,
                    "sender_is_bot": sender_is_bot,
                    "reply_to_msg_id": getattr(message.reply_to, "reply_to_msg_id", None),
                    "has_media": bool(message.media),
                    "views": message.views,
                    "forwards": message.forwards,
                    "text": (message.message or "").strip(),
                }
            )

    messages.sort(key=lambda item: item["id"])

    run_started = utc_now()
    chat_output_dir = OUTPUT_ROOT / chat_slug
    ensure_directory(chat_output_dir)
    daily_path = chat_output_dir / f"{run_started.strftime('%Y-%m-%d')}.json"
    daily_payload = load_json(
        daily_path,
        default={
            "chat": args.chat,
            "chat_slug": chat_slug,
            "title": title,
            "chat_id": chat_id,
            "generated_at": run_started.isoformat(),
            "messages": [],
        },
    )

    merged = {item["id"]: item for item in daily_payload.get("messages", [])}
    for item in messages:
        merged[item["id"]] = item

    merged_messages = [merged[key] for key in sorted(merged)]
    save_json(
        daily_path,
        {
            "chat": args.chat,
            "chat_slug": chat_slug,
            "title": title,
            "chat_id": chat_id,
            "generated_at": run_started.isoformat(),
            "messages": merged_messages,
        },
    )

    last_after = merged_messages[-1]["id"] if merged_messages else last_message_id
    save_json(
        state_path,
        {
            "chat": args.chat,
            "chat_slug": chat_slug,
            "title": title,
            "chat_id": chat_id,
            "last_message_id": last_after,
            "last_run_utc": run_started.isoformat(),
            "last_daily_file": str(daily_path),
        },
    )

    result = {
        "chat": args.chat,
        "chat_slug": chat_slug,
        "title": title,
        "fetched_new_messages": len(messages),
        "last_message_id_before": last_message_id,
        "last_message_id_after": last_after,
        "daily_file": str(daily_path),
        "state_file": str(state_path),
    }
    save_json(chat_output_dir / "latest_fetch.json", result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
