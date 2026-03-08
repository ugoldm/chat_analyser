import re
from collections import Counter
from datetime import datetime, timedelta, timezone


items_in = items if "items" in globals() else []
payload = items_in[0]["json"] if items_in else {}

chat = payload["chat"]
current_batch = payload["current_batch"]
history_batches = payload.get("history_batches", [])

STOPWORDS = {
    "это", "как", "что", "для", "или", "если", "при", "так", "уже", "еще", "ещё",
    "только", "меня", "мне", "вам", "нас", "вас", "они", "она", "оно", "его", "ее",
    "её", "мы", "вы", "ты", "мой", "моя", "мои", "ваш", "ваши", "когда", "где",
    "кто", "чтобы", "после", "перед", "тут", "там", "вот", "просто", "тоже",
    "сейчас", "потом", "можно", "нужно", "надо", "было", "быть", "есть", "нет",
    "да", "под", "над", "из", "за", "от", "до", "по", "на", "в", "во", "не", "ни",
    "но", "а", "и", "или", "же", "ли", "бы", "спасибо", "пожалуйста", "здравствуйте",
    "добрый", "день",
}

TOPIC_KEYWORDS = {
    "checks_and_receipts": ["чек", "чеки", "квитанция", "мойналог", "сформировать", "аннулировать"],
    "taxes_and_rates": ["налог", "налоги", "ставка", "ставки", "ндс", "ндфл", "оплата", "уплата", "доход"],
    "clients_and_contracts": ["договор", "акт", "клиент", "заказчик", "юрлицо", "контрагент"],
    "banking_and_payments": ["банк", "карта", "сбер", "тинькофф", "перевод", "эквайринг", "расчетный"],
    "reporting_and_fns": ["фнс", "налоговая", "декларация", "отчет", "отчёт", "уведомление"],
    "limits_and_eligibility": ["лимит", "патент", "работодатель", "совмещение", "нельзя"],
}

PAIN_PATTERNS = [
    {"id": "tax_payment_visibility", "title": "Неясно, когда появляется и как подтверждается оплата налога", "keywords": ["оплата", "оплатить", "налог", "висит", "сумма"]},
    {"id": "my_tax_app_instability", "title": "Сбои и непонятное поведение приложения Мой налог", "keywords": ["мой", "налог", "приложение", "сбой", "работает", "висит"]},
    {"id": "refunds_and_corrections", "title": "Возвраты, отмены и корректировки уже проведённых оплат", "keywords": ["возврат", "вернуть", "предоплата", "аннулировать"]},
    {"id": "receipt_after_platform_payouts", "title": "Как правильно пробивать чек при выплатах от платформ и маркетплейсов", "keywords": ["чек", "авито", "озон", "ozon", "платформа", "выплата"]},
    {"id": "intermediary_and_agent_income", "title": "Сложно определить, на кого оформлять чек при посредниках и агентских схемах", "keywords": ["чек", "клиент", "платформа", "агент", "юрлицо"]},
    {"id": "bank_card_risks", "title": "Риски блокировок карт и подозрений со стороны банков", "keywords": ["карта", "банк", "сбер", "блокиров", "перевод"]},
    {"id": "fns_and_reporting_confusion", "title": "Путаница с декларациями, ФНС и обязательной отчётностью", "keywords": ["декларация", "фнс", "налоговая", "отчет", "отчёт"]},
    {"id": "social_fund_and_sick_leave", "title": "Непонимание добровольных взносов, больничных и Соцфонда", "keywords": ["больнич", "взнос", "страхование", "фсс", "фонд"]},
    {"id": "fraud_and_social_engineering", "title": "Мошеннические звонки под видом налоговой", "keywords": ["код", "позвонили", "налоговую", "прокуратура", "мошен"]},
]


def tokenize(text):
    tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9_]{3,}", (text or "").lower())
    return [token for token in tokens if token not in STOPWORDS]


def top_terms(messages, limit=20):
    counter = Counter()
    for message in messages:
        counter.update(tokenize(message.get("text", "")))
    return [{"term": term, "count": count} for term, count in counter.most_common(limit)]


def topic_counts(messages):
    counts = Counter()
    for message in messages:
        tokens = set(tokenize(message.get("text", "")))
        for topic, words in TOPIC_KEYWORDS.items():
            if any(word in tokens for word in words):
                counts[topic] += 1
    return counts


def pain_points(messages, limit=15):
    result = []
    for pattern in PAIN_PATTERNS:
        matched = []
        for message in messages:
            tokens = set(tokenize(message.get("text", "")))
            if any(any(token.startswith(keyword) or keyword in token for token in tokens) for keyword in pattern["keywords"]):
                matched.append(message)
        if not matched:
            continue
        matched.sort(key=lambda item: len(item.get("text", "")), reverse=True)
        sample = matched[0]
        result.append(
            {
                "id": pattern["id"],
                "title": pattern["title"],
                "matches": len(matched),
                "sample_date": sample.get("date"),
                "sample_sender": sample.get("sender_name") or str(sample.get("sender_id")),
                "sample_text": (sample.get("text") or "")[:320],
            }
        )
    return sorted(result, key=lambda item: item["matches"], reverse=True)[:limit]


def representative_questions(messages, limit=10):
    result = []
    for message in messages:
        if "?" in (message.get("text") or ""):
            result.append(
                {
                    "date": message.get("date"),
                    "sender_name": message.get("sender_name") or str(message.get("sender_id")),
                    "text": (message.get("text") or "")[:320],
                }
            )
    result.sort(key=lambda item: len(item["text"]), reverse=True)
    return result[:limit]


def top_authors(messages, limit=10):
    counter = Counter()
    names = {}
    for message in messages:
        sender_id = message.get("sender_id", 0)
        counter[sender_id] += 1
        if message.get("sender_name") and sender_id not in names:
            names[sender_id] = message["sender_name"]
    return [
        {
            "sender_id": sender_id,
            "sender_name": names.get(sender_id, str(sender_id)),
            "messages": count,
        }
        for sender_id, count in counter.most_common(limit)
    ]


def dedup_messages(all_messages):
    by_id = {}
    for message in all_messages:
        by_id[message["id"]] = message
    return [by_id[key] for key in sorted(by_id)]


all_messages = []
for batch in history_batches:
    batch_json = batch.get("json", batch)
    all_messages.extend(batch_json.get("messages", []))

all_messages.extend(current_batch.get("messages", []))
all_messages = dedup_messages(all_messages)

now = datetime.now(timezone.utc)
current_start = now - timedelta(days=1)
baseline_start = current_start - timedelta(days=7)

current_messages = []
baseline_messages = []
for message in all_messages:
    raw_dt = message.get("date")
    if not raw_dt:
        continue
    dt = datetime.fromisoformat(raw_dt)
    if current_start <= dt < now:
        current_messages.append(message)
    elif baseline_start <= dt < current_start:
        baseline_messages.append(message)

user_messages = [m for m in current_messages if (m.get("text") or "") and not m.get("sender_is_bot") and m.get("sender_id", 0) > 0]
baseline_user_messages = [m for m in baseline_messages if (m.get("text") or "") and not m.get("sender_is_bot") and m.get("sender_id", 0) > 0]

current_topic_counts = topic_counts(user_messages)
baseline_topic_counts = topic_counts(baseline_user_messages)

trends = []
for topic, count in current_topic_counts.items():
    baseline_avg = baseline_topic_counts.get(topic, 0) / 7.0
    delta = round(count - baseline_avg, 2)
    direction = "flat"
    if delta > 0.5:
        direction = "up"
    elif delta < -0.5:
        direction = "down"
    trends.append(
        {
            "topic": topic,
            "current_count": count,
            "baseline_avg_per_day": round(baseline_avg, 2),
            "delta_vs_baseline": delta,
            "direction": direction,
        }
    )

summary = {
    "chat": chat,
    "messages_in_period": len(current_messages),
    "user_text_messages": len(user_messages),
    "reply_messages": sum(1 for message in current_messages if message.get("reply_to_msg_id")),
    "media_messages": sum(1 for message in current_messages if message.get("has_media")),
    "top_authors": top_authors(current_messages),
    "topic_counts": dict(current_topic_counts),
    "top_terms": top_terms(user_messages, 25),
    "pain_points": pain_points(user_messages, 15),
    "representative_questions": representative_questions(current_messages, 10),
    "trends": trends,
    "period_from": current_start.isoformat(),
    "period_to": now.isoformat(),
}

llm_input = {
    "task": "Проанализируй сообщения чата за текущий период и верни JSON.",
    "required_output": {
        "executive_summary": "string",
        "key_trends": ["string"],
        "notable_shifts": ["string"],
        "recommended_actions": ["string"],
        "answer_to_custom_prompt": "string",
    },
    "custom_prompt": "Какие вопросы сейчас волнуют аудиторию больше всего и почему?",
    "summary": summary,
}

return [{"json": {"chat": chat, "summary": summary, "llm_input": llm_input}}]
