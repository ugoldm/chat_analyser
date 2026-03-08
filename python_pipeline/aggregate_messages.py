import argparse
import json
from pathlib import Path

from pipeline.analysis_core import (
    build_analysis_payload,
    ensure_directory,
    load_json,
    load_raw_messages,
    save_json,
    slugify_chat,
    split_message_windows,
    utc_now,
)


RAW_ROOT = Path(__file__).with_name("output") / "raw"
PROCESSED_ROOT = Path(__file__).with_name("output") / "processed"
STATE_DIR = Path(__file__).with_name("state")
PROMPTS_DIR = Path(__file__).with_name("prompts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate raw Telegram messages into analysis JSON.")
    parser.add_argument("--chat", required=True, help="Chat username or link.")
    parser.add_argument("--analysis-days", type=int, default=1, help="Days in the current analysis window.")
    parser.add_argument("--baseline-days", type=int, default=7, help="Days in the baseline window.")
    parser.add_argument("--prompt-file", default=str(PROMPTS_DIR / "daily_analysis.txt"), help="Path to the custom prompt template.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chat_slug = slugify_chat(args.chat)
    raw_chat_dir = RAW_ROOT / chat_slug
    processed_chat_dir = PROCESSED_ROOT / chat_slug
    state_path = STATE_DIR / f"{chat_slug}.json"
    ensure_directory(processed_chat_dir)

    all_messages = load_raw_messages(raw_chat_dir)
    if not all_messages:
        raise SystemExit(f"No raw messages found in {raw_chat_dir}")

    state = load_json(state_path, default={})
    title = state.get("title", args.chat)
    prompt_text = Path(args.prompt_file).read_text(encoding="utf-8").strip()

    period_end = utc_now()
    current_messages, baseline_messages, current_start, current_end = split_message_windows(
        all_messages,
        analysis_days=args.analysis_days,
        baseline_days=args.baseline_days,
        end_at=period_end,
    )

    payload = build_analysis_payload(
        chat=args.chat,
        title=title,
        all_messages=all_messages,
        current_messages=current_messages,
        baseline_messages=baseline_messages,
        current_start=current_start,
        current_end=current_end,
        analysis_days=args.analysis_days,
        baseline_days=args.baseline_days,
        custom_prompt=prompt_text,
    )
    payload["generated_at"] = period_end.isoformat()

    latest_path = processed_chat_dir / "latest_analysis.json"
    dated_path = processed_chat_dir / f"{period_end.strftime('%Y-%m-%d')}_analysis.json"
    llm_input_path = processed_chat_dir / "latest_llm_input.json"

    save_json(latest_path, payload)
    save_json(dated_path, payload)
    save_json(llm_input_path, payload["llm_input"])

    result = {
        "analysis_path": str(latest_path),
        "dated_analysis_path": str(dated_path),
        "llm_input_path": str(llm_input_path),
        "messages_in_period": payload["summary"]["messages_in_period"],
        "baseline_messages": len(baseline_messages),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
