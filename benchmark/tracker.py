import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from actions.types import Action


@dataclass
class StepRecord:
    step: int
    action_type: str
    details: dict
    timestamp: float


@dataclass
class BenchmarkTracker:
    task: str
    model_name: str
    session_dir: Optional[Path] = None
    steps: list = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    success: Optional[bool] = None
    error: Optional[str] = None

    def start(self) -> None:
        self.start_time = time.time()

    def record_step(self, action: Action) -> None:
        self.steps.append(
            StepRecord(
                step=len(self.steps) + 1,
                action_type=action.type.value,
                details={k: v for k, v in action.to_dict().items() if k != "type"},
                timestamp=time.time(),
            )
        )

    def finish(self, success: bool, error: Optional[str] = None) -> None:
        self.end_time = time.time()
        self.success = success
        self.error = error
        if self.session_dir:
            self.save(self.session_dir)

    @property
    def elapsed_seconds(self) -> float:
        if self.start_time is None:
            return 0.0
        return round((self.end_time or time.time()) - self.start_time, 2)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    def summary(self) -> dict:
        return {
            "task": self.task,
            "model": self.model_name,
            "success": self.success,
            "total_steps": self.total_steps,
            "elapsed_seconds": self.elapsed_seconds,
            "error": self.error,
        }

    def save(self, directory: Optional[Path] = None) -> Path:
        out_dir = directory or self.session_dir or Path("data/sessions")
        out_dir.mkdir(parents=True, exist_ok=True)
        results_file = out_dir / "results.json"
        data = {
            "summary": self.summary(),
            "steps": [
                {
                    "step": s.step,
                    "action": s.action_type,
                    "details": s.details,
                    "timestamp": s.timestamp,
                }
                for s in self.steps
            ],
        }
        results_file.write_text(json.dumps(data, indent=2))
        return results_file


def make_session_dir(task: str, model_name: str) -> Path:
    """
    Create and return a timestamped session directory under data/sessions/.
    e.g.  data/sessions/20260311_143022_open-browser_gpt-4o/
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", task.lower())[:30].strip("-")
    model_slug = re.sub(r"[^a-z0-9]+", "-", model_name.lower())
    name = f"{timestamp}_{slug}_{model_slug}"
    session_dir = Path("data") / "sessions" / name
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "screenshots").mkdir(exist_ok=True)
    return session_dir
