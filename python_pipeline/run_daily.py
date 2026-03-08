import argparse
import os
import subprocess
import sys
from pathlib import Path

from pipeline.analysis_core import slugify_chat


ROOT = Path(__file__).parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standalone Python pipeline.")
    parser.add_argument("--chat", default=os.getenv("DEFAULT_CHAT", "selfworkchat"), help="Chat username or link.")
    parser.add_argument("--fetch-limit", type=int, default=int(os.getenv("FETCH_LIMIT", "5000")), help="Maximum new messages to fetch.")
    parser.add_argument("--analysis-days", type=int, default=1, help="Days in the current analysis window.")
    parser.add_argument("--baseline-days", type=int, default=7, help="Days in the baseline window.")
    parser.add_argument("--skip-llm", action="store_true", help="Skip the LLM step even if LLM credentials are available.")
    return parser.parse_args()


def run_step(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    args = parse_args()
    run_step(
        [
            sys.executable,
            "telegram_fetch.py",
            "--chat",
            args.chat,
            "--limit",
            str(args.fetch_limit),
        ]
    )
    run_step(
        [
            sys.executable,
            "aggregate_messages.py",
            "--chat",
            args.chat,
            "--analysis-days",
            str(args.analysis_days),
            "--baseline-days",
            str(args.baseline_days),
        ]
    )

    chat_slug = slugify_chat(args.chat)
    processed_dir = ROOT / "output" / "processed" / chat_slug
    analysis_json = processed_dir / "latest_analysis.json"
    llm_json = processed_dir / "latest_llm_output.json"

    if not args.skip_llm and os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL"):
        run_step(
            [
                sys.executable,
                "llm_client.py",
                "--analysis-json",
                str(analysis_json),
                "--output-json",
                str(llm_json),
            ]
        )

    render_command = [sys.executable, "render_report.py", "--analysis-json", str(analysis_json)]
    if llm_json.exists():
        render_command.extend(["--llm-json", str(llm_json)])
    run_step(render_command)


if __name__ == "__main__":
    main()
