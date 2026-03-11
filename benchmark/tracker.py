import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

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
    steps: List[StepRecord] = field(default_factory=list)
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

    @property
    def elapsed_seconds(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return round(end - self.start_time, 2)

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

    def save(self, path: str = "results") -> Path:
        out_dir = Path(path)
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        filename = out_dir / f"{self.model_name}_{timestamp}.json"
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
        filename.write_text(json.dumps(data, indent=2))
        return filename
