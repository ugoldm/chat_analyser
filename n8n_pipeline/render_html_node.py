import html


items_in = items if "items" in globals() else []
payload = items_in[0]["json"] if items_in else {}

summary = payload["summary"]
llm_output = payload.get("llm_output", {})


def table(rows, headers):
    if not rows:
        return "<p>No data</p>"
    body = "".join(
        f"<tr><td>{html.escape(str(left))}</td><td>{html.escape(str(right))}</td></tr>"
        for left, right in rows
    )
    return f"<table><thead><tr><th>{html.escape(headers[0])}</th><th>{html.escape(headers[1])}</th></tr></thead><tbody>{body}</tbody></table>"


metric_rows = [
    ("Messages in period", summary["messages_in_period"]),
    ("User text messages", summary["user_text_messages"]),
    ("Reply messages", summary["reply_messages"]),
    ("Media messages", summary["media_messages"]),
    ("Period", f"{summary['period_from']} -> {summary['period_to']}"),
]
topic_rows = [(key, value) for key, value in summary["topic_counts"].items()]
term_rows = [(item["term"], item["count"]) for item in summary["top_terms"][:15]]
author_rows = [(item["sender_name"], item["messages"]) for item in summary["top_authors"][:10]]
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

llm_summary = html.escape(str(llm_output.get("executive_summary", "")))
llm_answer = html.escape(str(llm_output.get("answer_to_custom_prompt", "")))
llm_trends = "".join(f"<li>{html.escape(str(item))}</li>" for item in llm_output.get("key_trends", []))
llm_actions = "".join(f"<li>{html.escape(str(item))}</li>" for item in llm_output.get("recommended_actions", []))

report_html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Daily Telegram Analysis</title>
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
  </style>
</head>
<body>
  <div class="wrap">
    <div class="section">
      <h1>Daily Telegram Analysis</h1>
      <p><strong>Chat:</strong> {html.escape(payload.get("chat", "unknown"))}</p>
      {table(metric_rows, ("Metric", "Value"))}
    </div>

    <div class="section">
      <h2>Главные боли аудитории</h2>
      <ol>{pain_html}</ol>
    </div>

    <div class="section">
      <h2>Trend Changes</h2>
      {table(trend_rows, ("Topic", "Trend"))}
    </div>

    <div class="section">
      <h2>Top Topics</h2>
      {table(topic_rows, ("Topic", "Messages"))}
    </div>

    <div class="section">
      <h2>Top Terms</h2>
      {table(term_rows, ("Term", "Count"))}
    </div>

    <div class="section">
      <h2>Top Authors</h2>
      {table(author_rows, ("Author", "Messages"))}
    </div>

    <div class="section">
      <h2>Representative Questions</h2>
      <ul>{question_html}</ul>
    </div>

    <div class="section">
      <h2>LLM Analysis</h2>
      <p>{llm_summary}</p>
      <h3>Key Trends</h3>
      <ul>{llm_trends}</ul>
      <h3>Recommended Actions</h3>
      <ul>{llm_actions}</ul>
      <h3>Custom Prompt Answer</h3>
      <p>{llm_answer}</p>
    </div>
  </div>
</body>
</html>
"""

return [{"json": {"chat": payload.get("chat"), "report_html": report_html, "summary": summary, "llm_output": llm_output}}]
