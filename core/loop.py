import json
import time
from pathlib import Path
from typing import Optional

from PIL import ImageStat
from rich.console import Console
from rich.panel import Panel

from actions.types import Action, ActionType
from benchmark.tracker import BenchmarkTracker
from core import executor, screen, sysinfo
from models.base import BaseModel

console = Console()

BLANK_BRIGHTNESS_THRESHOLD = 5.0


def _check_screenshot(img) -> tuple[bool, str]:
    stat = ImageStat.Stat(img)
    mean = sum(stat.mean[:3]) / 3
    stddev = sum(stat.stddev[:3]) / 3
    if mean < BLANK_BRIGHTNESS_THRESHOLD and stddev < 1.0:
        return False, (
            f"Screenshot is blank (mean={mean:.1f}/255, stddev={stddev:.1f}). "
            "Display may not be active or screen capture backend returned an empty frame."
        )
    return True, ""


def _save_screenshot(img, directory: Optional[Path], name: str) -> None:
    if directory is None:
        return
    img.save(directory / "screenshots" / f"{name}.png")


def run(
    model: BaseModel,
    task: str,
    max_steps: int = 50,
    tracker: Optional[BenchmarkTracker] = None,
    session_dir: Optional[Path] = None,
) -> BenchmarkTracker:
    """
    Main action loop.

    Pre-flight:
      1. Collect OS / desktop / display info
      2. Take one screenshot and validate it is not blank
      3. Write session metadata.json

    Loop (up to max_steps):
      1. Take screenshot  (saved to session_dir/screenshots/step_NNN.png)
      2. Send to model with task + sysinfo + history
      3. Parse action
      4. Execute action
      5. Repeat until done or max_steps
    """
    if tracker is None:
        tracker = BenchmarkTracker(
            task=task,
            model_name=model.model_name,
            session_dir=session_dir,
        )

    console.print(Panel(f"[bold]Task:[/bold] {task}", title="CUA Facilitator"))

    # --- PRE-FLIGHT: screenshot + sysinfo ---
    img, screenshot_b64 = screen.capture()
    width, height = img.size

    info = sysinfo.gather(screen_width=width, screen_height=height)
    console.print(f"[dim]System:[/dim] {info.as_prompt_text()}")

    if session_dir:
        _write_metadata(session_dir, task, model, info)
        _save_screenshot(img, session_dir, "preflight")

    # --- PRE-FLIGHT: blank screen check ---
    valid, reason = _check_screenshot(img)
    if not valid:
        console.print(f"[bold red]Pre-flight failed:[/bold red] {reason}")
        console.print(
            "[yellow]Hint:[/yellow] Check that the display is active.\n"
            "  Linux Wayland (GNOME): ensure xdg-desktop-portal-gnome is running.\n"
            "  Linux X11:             ensure DISPLAY is set correctly.\n"
            "  macOS:                 grant Screen Recording permission."
        )
        tracker.start()
        tracker.finish(success=False, error=f"blank_screenshot: {reason}")
        return tracker

    sysinfo_text = info.as_prompt_text()
    history = []
    tracker.start()

    for step in range(1, max_steps + 1):
        console.rule(f"Step {step}/{max_steps}")

        img, screenshot_b64 = screen.capture()
        _save_screenshot(img, session_dir, f"step_{step:03d}")

        try:
            action = _call_model_with_retry(
                model, screenshot_b64, task, history,
                width, height, sysinfo_text,
            )
        except Exception as exc:
            console.print(f"[red]Model error:[/red] {exc}")
            tracker.finish(success=False, error=str(exc))
            return tracker

        _log_action(action, step)
        tracker.record_step(action)

        if action.type == ActionType.DONE:
            console.print(f"[green]Done:[/green] {action.result}")
            tracker.finish(success=True)
            return tracker

        try:
            executor.execute(action)
        except Exception as exc:
            console.print(f"[red]Execution error:[/red] {exc}")
            tracker.finish(success=False, error=str(exc))
            return tracker

        history.append(action.to_dict())

    console.print("[yellow]Max steps reached without completion.[/yellow]")
    tracker.finish(success=False, error="max_steps_exceeded")
    return tracker


def _call_model_with_retry(
    model: BaseModel,
    screenshot_b64: str,
    task: str,
    history: list,
    width: int,
    height: int,
    sysinfo_text: Optional[str],
) -> Action:
    """
    Call the model and retry once on empty/parse failures.
    A brief sleep before the retry handles transient API hiccups.
    """
    last_exc: Exception | None = None
    for attempt in range(2):
        if attempt > 0:
            console.print(f"[yellow]Retrying model call (attempt {attempt + 1}/2)...[/yellow]")
            time.sleep(2.0)
        try:
            return model.get_action(
                screenshot_b64=screenshot_b64,
                task=task,
                history=history,
                screen_width=width,
                screen_height=height,
                sysinfo_text=sysinfo_text,
            )
        except Exception as exc:
            last_exc = exc
    raise last_exc


def _write_metadata(
    session_dir: Path,
    task: str,
    model: BaseModel,
    info,
) -> None:
    meta = {
        "task": task,
        "model": model.model_name,
        "system": info.as_dict(),
    }
    (session_dir / "metadata.json").write_text(json.dumps(meta, indent=2))


def _log_action(action: Action, step: int) -> None:
    reasoning = action.reasoning or ""
    details = {k: v for k, v in action.to_dict().items() if k not in ("reasoning", "type")}
    console.print(
        f"[cyan]{action.type.value}[/cyan]  {details}"
        + (f"\n  [dim]{reasoning}[/dim]" if reasoning else "")
    )
