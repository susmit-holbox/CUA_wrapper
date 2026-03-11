from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ActionType(str, Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEY = "key"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    DONE = "done"
    WAIT = "wait"


@dataclass
class Action:
    type: ActionType
    # click / double_click / right_click / scroll
    x: Optional[int] = None
    y: Optional[int] = None
    # scroll direction and amount
    direction: Optional[str] = None  # "up" | "down" | "left" | "right"
    amount: Optional[int] = None
    # type / key
    text: Optional[str] = None
    # wait
    seconds: Optional[float] = None
    # model reasoning (not executed)
    reasoning: Optional[str] = None
    # done result message
    result: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        action_type = ActionType(data["action"])
        return cls(
            type=action_type,
            x=data.get("x"),
            y=data.get("y"),
            direction=data.get("direction"),
            amount=data.get("amount"),
            text=data.get("text"),
            seconds=data.get("seconds"),
            reasoning=data.get("reasoning"),
            result=data.get("result"),
        )

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}
