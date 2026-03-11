#!/usr/bin/env python3
"""
CUA Facilitator - model-agnostic Computer Use Agent testbed.

Usage:
    python main.py --provider anthropic --task "Open Firefox and go to google.com"
    python main.py --provider openai    --task "Take a screenshot and tell me what you see" --max-steps 5
    python main.py --provider google    --task "Open the terminal" --save-results
"""
import argparse
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()

# pynput on Linux uses XWayland (via DISPLAY) when available.
# Set a fallback so it can find the X server when running inside an IDE terminal.
if not os.environ.get("DISPLAY"):
    os.environ["DISPLAY"] = ":0"

PROVIDERS = ("anthropic", "openai", "google")


def build_model(provider: str, model_name: str | None):
    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        from models.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key, model_name=model_name or "claude-opus-4-5")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        from models.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model_name=model_name or "gpt-4o")

    if provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY", "")
        from models.google_provider import GoogleProvider
        return GoogleProvider(api_key=api_key, model_name=model_name or "gemini-1.5-pro")

    console.print(f"[red]Unknown provider '{provider}'. Choose from: {PROVIDERS}[/red]")
    sys.exit(1)


def print_summary(tracker) -> None:
    s = tracker.summary()
    table = Table(title="Run Summary", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for k, v in s.items():
        table.add_row(str(k), str(v))
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="CUA Facilitator")
    parser.add_argument("--provider", required=True, choices=PROVIDERS,
                        help="Model provider to use")
    parser.add_argument("--model", default=None,
                        help="Override the default model name for the provider")
    parser.add_argument("--task", required=True,
                        help="Natural language task for the agent to perform")
    parser.add_argument("--max-steps", type=int, default=50,
                        help="Maximum number of actions before giving up (default: 50)")
    parser.add_argument("--no-save", action="store_true",
                        help="Skip saving session data to disk")
    args = parser.parse_args()

    model = build_model(args.provider, args.model)
    console.print(f"[dim]Provider:[/dim] {args.provider}  [dim]Model:[/dim] {model.model_name}")

    from benchmark.tracker import make_session_dir
    from core.loop import run

    session_dir = None if args.no_save else make_session_dir(args.task, model.model_name)
    if session_dir:
        console.print(f"[dim]Session:[/dim] {session_dir}")

    tracker = run(model=model, task=args.task, max_steps=args.max_steps, session_dir=session_dir)

    print_summary(tracker)


if __name__ == "__main__":
    main()
