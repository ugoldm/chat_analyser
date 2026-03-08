import argparse
import json
from pathlib import Path

from pipeline.analysis_core import ensure_directory, load_json, render_html_report, save_json, slugify_chat, utc_now


REPORT_ROOT = Path(__file__).with_name("output") / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render an HTML report from analysis JSON.")
    parser.add_argument("--analysis-json", required=True, help="Path to latest_analysis.json")
    parser.add_argument("--llm-json", default="", help="Optional path to latest_llm_output.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analysis_payload = load_json(Path(args.analysis_json), default={})
    llm_payload = load_json(Path(args.llm_json), default=None) if args.llm_json else None

    chat_slug = slugify_chat(analysis_payload["chat"])
    report_dir = REPORT_ROOT / chat_slug
    ensure_directory(report_dir)

    generated_at = utc_now().isoformat()
    report_html = render_html_report(analysis_payload, llm_payload, generated_at)

    latest_path = report_dir / "latest.html"
    dated_path = report_dir / f"{generated_at[:10]}.html"
    latest_path.write_text(report_html, encoding="utf-8")
    dated_path.write_text(report_html, encoding="utf-8")

    manifest = {
        "report_latest": str(latest_path),
        "report_dated": str(dated_path),
        "analysis_json": str(args.analysis_json),
        "llm_json": str(args.llm_json) if args.llm_json else None,
        "generated_at": generated_at,
    }
    save_json(report_dir / "latest_report.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
