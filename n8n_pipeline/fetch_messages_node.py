import os
import asyncio
from datetime import timezone

from telethon import TelegramClient
from telethon.sessions import StringSession


items_in = items if "items" in globals() else []
state_item = items_in[0]["json"] if items_in else {}

api_id = int(os.environ["TG_API_ID"])
api_hash = os.environ["TG_API_HASH"]
string_session = os.environ["TG_STRING_SESSION"]
chat_ref = os.environ.get("TG_CHAT", "selfworkchat")

last_message_id = int(state_item.get("last_message_id", 0) or 0)


async def main():
    client = TelegramClient(StringSession(string_session), api_id, api_hash)
    await client.connect()

    entity = await client.get_entity(chat_ref)
    if last_message_id > 0:
        fetched = await client.get_messages(entity, limit=300, min_id=last_message_id)
    else:
        fetched = await client.get_messages(entity, limit=300)

    result_messages = []
    for msg in fetched:
        sender = getattr(msg, "sender", None)
        sender_name = None
        sender_is_bot = False
        if sender:
            first = getattr(sender, "first_name", "") or ""
            last = getattr(sender, "last_name", "") or ""
            username = getattr(sender, "username", "") or ""
            sender_is_bot = bool(getattr(sender, "bot", False))
            sender_name = " ".join([part for part in [first, last] if part]).strip() or (f"@{username}" if username else None)

        sender_id = 0
        if getattr(msg, "sender_id", None) is not None:
            sender_id = int(
                getattr(msg.sender_id, "user_id", None)
                or getattr(msg.sender_id, "channel_id", None)
                or getattr(msg.sender_id, "chat_id", None)
                or 0
            )

        reply_to_msg_id = None
        if getattr(msg, "reply_to", None):
            reply_to_msg_id = getattr(msg.reply_to, "reply_to_msg_id", None)

        result_messages.append(
            {
                "id": msg.id,
                "date": msg.date.astimezone(timezone.utc).isoformat() if msg.date else None,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "sender_is_bot": sender_is_bot,
                "reply_to_msg_id": reply_to_msg_id,
                "has_media": bool(msg.media),
                "views": getattr(msg, "views", None),
                "forwards": getattr(msg, "forwards", None),
                "text": (msg.message or "").strip(),
            }
        )

    result_messages.sort(key=lambda item: item["id"])
    await client.disconnect()

    last_after = last_message_id
    if result_messages:
        last_after = result_messages[-1]["id"]

    return {
        "chat": chat_ref,
        "fetched_count": len(result_messages),
        "last_message_id_before": last_message_id,
        "last_message_id_after": last_after,
        "messages": result_messages,
    }


result = asyncio.run(main())
return [{"json": result}]
