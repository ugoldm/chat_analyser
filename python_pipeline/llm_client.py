import argparse
import json
import os
import urllib.request
from pathlib import Path

from pipeline.analysis_core import load_json, save_json


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call an OpenAI-compatible LLM endpoint.")
    parser.add_argument("--analysis-json", required=True, help="Path to the analysis JSON.")
    parser.add_argument("--output-json", default="", help="Optional path for the structured LLM response.")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    return parser.parse_args()


def build_messages(payload: dict) -> list[dict]:
    return [
        {
            "role": "system",
            "content": "Ты аналитик Telegram-чатов. Верни только валидный JSON без markdown и пояснений.",
        },
        {
            "role": "user",
            "content": json.dumps(payload["llm_input"], ensure_ascii=False),
        },
    ]


def main() -> None:
    args = parse_args()
    payload = load_json(Path(args.analysis_json), default={})

    api_key = require_env("LLM_API_KEY")
    model = require_env("LLM_MODEL")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    request_body = {
        "model": model,
        "temperature": args.temperature,
        "response_format": {"type": "json_object"},
        "messages": build_messages(payload),
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        raw_response = json.loads(response.read().decode("utf-8"))

    content = raw_response["choices"][0]["message"]["content"]
    parsed = json.loads(content)

    output_path = Path(args.output_json) if args.output_json else Path(args.analysis_json).parent / "latest_llm_output.json"
    save_json(output_path, parsed)
    print(json.dumps({"llm_output_path": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
