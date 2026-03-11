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
import subprocess
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()


def _ensure_display() -> None:
    """
    Make sure DISPLAY and XAUTHORITY are set so pyautogui can reach the X server.
    Needed when running from terminals (e.g. inside an IDE) that inherit a stripped env.
    """
    if not os.environ.get("DISPLAY"):
        os.environ["DISPLAY"] = ":0"

    if not os.environ.get("XAUTHORITY"):
        default = os.path.expanduser("~/.Xauthority")
        if os.path.exists(default):
            os.environ["XAUTHORITY"] = default

    # Grant local connections if xhost is available (silently ignore failures)
    subprocess.run(["xhost", "+local:"], capture_output=True)


_ensure_display()

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
    parser.add_argument("--save-results", action="store_true",
                        help="Save benchmark results to the results/ directory")
    args = parser.parse_args()

    model = build_model(args.provider, args.model)

    from core.loop import run
    tracker = run(model=model, task=args.task, max_steps=args.max_steps)

    print_summary(tracker)

    if args.save_results:
        path = tracker.save()
        console.print(f"[green]Results saved to:[/green] {path}")


if __name__ == "__main__":
    main()
