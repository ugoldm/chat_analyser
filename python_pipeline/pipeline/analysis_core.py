import html
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional


WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_]{3,}")
URL_RE = re.compile(r"(https?://\S+|t\.me/\S+)", re.IGNORECASE)
QUESTION_START_RE = re.compile(
    r"^\s*(кто|что|где|когда|зачем|почему|как|сколько|можно|нужно|подскажите|скажите)\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "это", "как", "что", "для", "или", "если", "при", "так", "уже", "еще", "ещё",
    "только", "меня", "мне", "вам", "нас", "вас", "они", "она", "оно", "его", "ее",
    "её", "мы", "вы", "ты", "моя", "мой", "мои", "твой", "ваш", "наша", "наш",
    "когда", "где", "кто", "чем", "чтобы", "после", "перед", "тут", "там", "вот",
    "просто", "тоже", "сейчас", "потом", "можно", "нужно", "надо", "было", "быть",
    "есть", "нет", "да", "под", "над", "из", "за", "от", "до", "по", "на", "в", "во",
    "не", "ни", "но", "а", "и", "или", "же", "ли", "бы", "мы", "вы", "он", "она",
    "они", "сам", "сама", "само", "самозанятый", "самозанятость", "самозанятые",
    "самозанятым", "самозанятого", "самозанятости", "ип", "ооо", "физлицо",
    "который", "которая", "которые", "которое", "этот", "эта", "эти", "того",
    "тогда", "здесь", "куда", "откуда", "либо", "лишь", "через", "между", "очень",
    "всех", "всем", "всё", "все", "ваше", "ваши", "будет", "будут", "был", "была",
    "были", "может", "могу", "смогу", "хочу", "хотел", "хотела", "сделать",
    "сказать", "подскажите", "скажите", "добрый", "день", "здравствуйте",
    "спасибо", "пожалуйста", "добрыйдень",
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
    {
        "id": "tax_payment_visibility",
        "title": "Неясно, когда появляется и как подтверждается оплата налога",
        "keywords": ["оплата", "оплатить", "налог", "висит", "сумма"],
    },
    {
        "id": "my_tax_app_instability",
        "title": "Сбои и непонятное поведение приложения Мой налог",
        "keywords": ["мой", "налог", "приложение", "сбой", "работает", "висит"],
    },
    {
        "id": "refunds_and_corrections",
        "title": "Возвраты, отмены и корректировки уже проведённых оплат",
        "keywords": ["возврат", "вернуть", "предоплата", "аннулировать"],
    },
    {
        "id": "receipt_after_platform_payouts",
        "title": "Как правильно пробивать чек при выплатах от платформ и маркетплейсов",
        "keywords": ["чек", "авито", "озон", "ozon", "платформа", "выплата"],
    },
    {
        "id": "intermediary_and_agent_income",
        "title": "Сложно определить, на кого оформлять чек при посредниках и агентских схемах",
        "keywords": ["чек", "клиент", "платформа", "агент", "юрлицо"],
    },
    {
        "id": "bank_card_risks",
        "title": "Риски блокировок карт и подозрений со стороны банков",
        "keywords": ["карта", "банк", "сбер", "блокиров", "перевод"],
    },
    {
        "id": "fns_and_reporting_confusion",
        "title": "Путаница с декларациями, ФНС и обязательной отчётностью",
        "keywords": ["декларация", "фнс", "налоговая", "отчет", "отчёт"],
    },
    {
        "id": "documents_and_wording",
        "title": "Как правильно оформлять документы, формулировки услуг и описание деятельности",
        "keywords": ["договор", "акт", "светодиод", "описание", "услуг", "наращивание"],
    },
    {
        "id": "registration_and_status_changes",
        "title": "Регистрация, смена статуса и бытовые последствия статуса самозанятого",
        "keywords": ["зарегистрироваться", "регистрация", "статус", "самозанятая", "мфц", "паспорт"],
    },
    {
        "id": "income_limits_and_eligibility",
        "title": "Неясные границы режима: лимиты, запреты и допустимые схемы работы",
        "keywords": ["лимит", "2400000", "можно", "нельзя", "работодатель", "патент"],
    },
    {
        "id": "combining_employment_and_self_employment",
        "title": "Совмещение работы по найму и самозанятости",
        "keywords": ["работодателю", "найме", "работаю", "зарегистрироваться", "совмещение", "трудовой"],
    },
    {
        "id": "social_fund_and_sick_leave",
        "title": "Непонимание добровольных взносов, больничных и Соцфонда",
        "keywords": ["больнич", "взнос", "страхование", "фсс", "фонд"],
    },
    {
        "id": "fraud_and_social_engineering",
        "title": "Мошеннические звонки под видом налоговой",
        "keywords": ["код", "позвонили", "налоговую", "прокуратура", "мошен"],
    },
]


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def slugify_chat(chat: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", chat).strip("_") or "chat"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in WORD_RE.findall((text or "").lower()):
        if token in STOPWORDS:
            continue
        if token.isdigit() and len(token) < 4:
            continue
        tokens.append(token)
    return tokens


def top_terms(texts: Iterable[str], limit: int = 20) -> list[dict]:
    counter = Counter()
    for text in texts:
        counter.update(tokenize(text))
    return [{"term": term, "count": count} for term, count in counter.most_common(limit)]


def compute_topic_counts(messages: list[dict]) -> Counter:
    counts = Counter()
    for message in messages:
        tokens = set(tokenize(message.get("text", "")))
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword in tokens for keyword in keywords):
                counts[topic] += 1
    return counts


def build_pain_points(messages: list[dict], limit: int = 15) -> list[dict]:
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
                "sample_text": sample.get("text", "")[:320],
            }
        )
    result.sort(key=lambda item: item["matches"], reverse=True)
    return result[:limit]


def representative_questions(messages: list[dict], limit: int = 12) -> list[dict]:
    questions = []
    for message in messages:
        text = message.get("text", "")
        if "?" in text or QUESTION_START_RE.search(text or ""):
            questions.append(
                {
                    "date": message.get("date"),
                    "sender_name": message.get("sender_name") or str(message.get("sender_id")),
                    "text": text[:320],
                }
            )
    questions.sort(key=lambda item: len(item["text"]), reverse=True)
    return questions[:limit]


def top_authors(messages: list[dict], limit: int = 10) -> list[dict]:
    counts = Counter()
    names = {}
    for message in messages:
        sender_id = message.get("sender_id", 0)
        counts[sender_id] += 1
        if message.get("sender_name") and sender_id not in names:
            names[sender_id] = message["sender_name"]
    return [
        {
            "sender_id": sender_id,
            "sender_name": names.get(sender_id, str(sender_id)),
            "messages": count,
        }
        for sender_id, count in counts.most_common(limit)
    ]


def deduplicate_messages(messages: list[dict]) -> list[dict]:
    by_id = {}
    for message in messages:
        by_id[message["id"]] = message
    return [by_id[key] for key in sorted(by_id)]


def load_raw_messages(raw_chat_dir: Path) -> list[dict]:
    if not raw_chat_dir.exists():
        return []
    messages = []
    for path in sorted(raw_chat_dir.glob("*.json")):
        payload = load_json(path, default={"messages": []})
        messages.extend(payload.get("messages", []))
    return deduplicate_messages(messages)


def split_message_windows(
    messages: list[dict],
    analysis_days: int,
    baseline_days: int,
    end_at: Optional[datetime] = None,
) -> tuple[list[dict], list[dict], datetime, datetime]:
    window_end = end_at or utc_now()
    current_start = window_end - timedelta(days=analysis_days)
    baseline_start = current_start - timedelta(days=baseline_days)

    current_messages = []
    baseline_messages = []
    for message in messages:
        dt = parse_iso_date(message.get("date"))
        if dt is None:
            continue
        if current_start <= dt < window_end:
            current_messages.append(message)
        elif baseline_start <= dt < current_start:
            baseline_messages.append(message)
    return current_messages, baseline_messages, current_start, window_end


def compute_activity_histograms(messages: list[dict]) -> tuple[list[dict], list[dict]]:
    daily = Counter()
    hourly = Counter()
    for message in messages:
        dt = parse_iso_date(message.get("date"))
        if dt is None:
            continue
        daily[dt.strftime("%Y-%m-%d")] += 1
        hourly[dt.strftime("%H:00")] += 1
    busiest_days = [{"day": day, "messages": count} for day, count in daily.most_common(10)]
    busiest_hours = [{"hour_utc": hour, "messages": count} for hour, count in hourly.most_common(10)]
    return busiest_days, busiest_hours


def compute_trends(current_counts: Counter, baseline_counts: Counter, baseline_days: int) -> list[dict]:
    trends = []
    for topic, current_count in current_counts.items():
        baseline_avg = baseline_counts.get(topic, 0) / float(max(baseline_days, 1))
        delta = round(current_count - baseline_avg, 2)
        direction = "flat"
        if delta > 0.5:
            direction = "up"
        elif delta < -0.5:
            direction = "down"
        trends.append(
            {
                "topic": topic,
                "current_count": current_count,
                "baseline_avg_per_day": round(baseline_avg, 2),
                "delta_vs_baseline": delta,
                "direction": direction,
            }
        )
    trends.sort(key=lambda item: item["delta_vs_baseline"], reverse=True)
    return trends


def build_analysis_payload(
    *,
    chat: str,
    title: str,
    all_messages: list[dict],
    current_messages: list[dict],
    baseline_messages: list[dict],
    current_start: datetime,
    current_end: datetime,
    analysis_days: int,
    baseline_days: int,
    custom_prompt: str,
) -> dict:
    text_messages = [m for m in current_messages if m.get("text")]
    user_messages = [m for m in text_messages if not m.get("sender_is_bot") and m.get("sender_id", 0) > 0]
    texts = [m["text"] for m in user_messages]

    current_topic_counts = compute_topic_counts(user_messages)
    baseline_topic_counts = compute_topic_counts(
        [m for m in baseline_messages if m.get("text") and not m.get("sender_is_bot") and m.get("sender_id", 0) > 0]
    )
    trends = compute_trends(current_topic_counts, baseline_topic_counts, baseline_days)

    summary = {
        "chat": chat,
        "title": title,
        "analysis_period": {
            "from": current_start.isoformat(),
            "to": current_end.isoformat(),
            "analysis_days": analysis_days,
            "baseline_days": baseline_days,
        },
        "messages_total_in_storage": len(all_messages),
        "messages_in_period": len(current_messages),
        "text_messages": len(text_messages),
        "user_text_messages": len(user_messages),
        "media_messages": sum(1 for m in current_messages if m.get("has_media")),
        "messages_with_links": sum(1 for m in text_messages if URL_RE.search(m.get("text", ""))),
        "reply_messages": sum(1 for m in current_messages if m.get("reply_to_msg_id")),
        "top_authors": top_authors(current_messages),
        "top_terms": top_terms(texts, limit=25),
        "topic_counts": dict(current_topic_counts),
        "pain_points": build_pain_points(user_messages, limit=15),
        "representative_questions": representative_questions(current_messages, limit=12),
        "trends": trends,
        "busiest_days": compute_activity_histograms(current_messages)[0],
        "busiest_hours_utc": compute_activity_histograms(current_messages)[1],
    }

    llm_input = {
        "task": "Проанализируй сообщения Telegram-чата и верни JSON-ответ по заданной схеме.",
        "custom_prompt": custom_prompt,
        "required_output": {
            "executive_summary": "string",
            "key_trends": ["string"],
            "notable_shifts": ["string"],
            "recommended_actions": ["string"],
            "answer_to_custom_prompt": "string",
        },
        "summary": summary,
    }

    return {
        "chat": chat,
        "title": title,
        "summary": summary,
        "llm_input": llm_input,
    }


def html_table(rows: list[tuple[str, str]], headers: tuple[str, str]) -> str:
    if not rows:
        return "<p class='muted'>No data</p>"
    body = "\n".join(
        f"<tr><td>{html.escape(str(left))}</td><td>{html.escape(str(right))}</td></tr>"
        for left, right in rows
    )
    return (
        "<table><thead><tr>"
        f"<th>{html.escape(headers[0])}</th><th>{html.escape(headers[1])}</th>"
        "</tr></thead><tbody>"
        f"{body}</tbody></table>"
    )


def render_html_report(analysis_payload: dict, llm_output: Optional[dict], generated_at: str) -> str:
    summary = analysis_payload["summary"]

    metric_rows = [
        ("Messages in period", summary["messages_in_period"]),
        ("User text messages", summary["user_text_messages"]),
        ("Reply messages", summary["reply_messages"]),
        ("Media messages", summary["media_messages"]),
        ("Messages with links", summary["messages_with_links"]),
        (
            "Period",
            f"{summary['analysis_period']['from']} -> {summary['analysis_period']['to']}",
        ),
    ]
    topic_rows = [(topic, count) for topic, count in summary["topic_counts"].items()]
    author_rows = [(item["sender_name"], item["messages"]) for item in summary["top_authors"]]
    term_rows = [(item["term"], item["count"]) for item in summary["top_terms"][:15]]
    trend_rows = [
        (
            item["topic"],
            f"{item['direction']} (current {item['current_count']}, baseline {item['baseline_avg_per_day']}/day)",
        )
        for item in summary["trends"][:10]
    ]

    pain_html = "".join(
        f"<li><h3>{html.escape(item['title'])}</h3><p><strong>Mentions:</strong> {item['matches']}</p><p>{html.escape(item['sample_text'])}</p></li>"
        for item in summary["pain_points"]
    )
    question_html = "".join(
        f"<li><p><strong>{html.escape(item['sender_name'])}</strong> · {html.escape(item['date'])}</p><p>{html.escape(item['text'])}</p></li>"
        for item in summary["representative_questions"]
    )

    llm_section = ""
    if llm_output:
        llm_trends = "".join(f"<li>{html.escape(str(item))}</li>" for item in llm_output.get("key_trends", []))
        llm_actions = "".join(f"<li>{html.escape(str(item))}</li>" for item in llm_output.get("recommended_actions", []))
        llm_section = f"""
    <section class="section">
      <h2>LLM Analysis</h2>
      <p>{html.escape(str(llm_output.get("executive_summary", "")))}</p>
      <h3>Key Trends</h3>
      <ul>{llm_trends}</ul>
      <h3>Recommended Actions</h3>
      <ul>{llm_actions}</ul>
      <h3>Custom Prompt Answer</h3>
      <p>{html.escape(str(llm_output.get("answer_to_custom_prompt", "")))}</p>
    </section>
"""

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(analysis_payload['title'])} - Daily Telegram Analysis</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7fb;
      color: #162033;
      margin: 0;
      padding: 24px;
      line-height: 1.5;
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    .section {{
      background: white;
      border: 1px solid #dde4ef;
      border-radius: 16px;
      padding: 20px;
      margin-bottom: 20px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      padding: 10px;
      border-bottom: 1px solid #e8edf5;
      vertical-align: top;
    }}
    h1, h2, h3 {{
      margin-top: 0;
    }}
    .muted {{
      color: #5b667a;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="section">
      <p class="muted">Generated at {html.escape(generated_at)}</p>
      <h1>{html.escape(analysis_payload['title'])}</h1>
      <p><strong>Chat:</strong> {html.escape(analysis_payload['chat'])}</p>
      {html_table(metric_rows, ("Metric", "Value"))}
    </div>

    <div class="section">
      <h2>Главные боли аудитории</h2>
      <ol>{pain_html}</ol>
    </div>

    <div class="section">
      <h2>Trend Changes</h2>
      {html_table(trend_rows, ("Topic", "Trend"))}
    </div>

    <div class="section">
      <h2>Top Topics</h2>
      {html_table(topic_rows, ("Topic", "Messages"))}
    </div>

    <div class="section">
      <h2>Top Terms</h2>
      {html_table(term_rows, ("Term", "Count"))}
    </div>

    <div class="section">
      <h2>Top Authors</h2>
      {html_table(author_rows, ("Author", "Messages"))}
    </div>

    <div class="section">
      <h2>Representative Questions</h2>
      <ul>{question_html}</ul>
    </div>
{llm_section}
  </div>
</body>
</html>
"""
