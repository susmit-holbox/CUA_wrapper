from typing import Optional

from rich.console import Console
from rich.panel import Panel

from actions.types import Action, ActionType
from benchmark.tracker import BenchmarkTracker
from core import executor, screen
from models.base import BaseModel

console = Console()


def run(
    model: BaseModel,
    task: str,
    max_steps: int = 50,
    tracker: Optional[BenchmarkTracker] = None,
) -> BenchmarkTracker:
    """
    Main action loop.

    1. Take screenshot
    2. Send to model with task + history
    3. Parse action
    4. Execute action
    5. Repeat until done or max_steps reached
    """
    if tracker is None:
        tracker = BenchmarkTracker(task=task, model_name=model.model_name)

    width, height = screen.screen_size()
    history = []

    tracker.start()
    console.print(Panel(f"[bold]Task:[/bold] {task}", title="CUA Facilitator"))

    for step in range(1, max_steps + 1):
        console.rule(f"Step {step}/{max_steps}")

        _, screenshot_b64 = screen.capture()

        try:
            action = model.get_action(
                screenshot_b64=screenshot_b64,
                task=task,
                history=history,
                screen_width=width,
                screen_height=height,
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


def _log_action(action: Action, step: int) -> None:
    reasoning = action.reasoning or ""
    details = {k: v for k, v in action.to_dict().items() if k not in ("reasoning", "type")}
    console.print(
        f"[cyan]{action.type.value}[/cyan]  {details}"
        + (f"\n  [dim]{reasoning}[/dim]" if reasoning else "")
    )
