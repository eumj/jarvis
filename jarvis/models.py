"""Data model, JSON persistence and task completion."""
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from jarvis.rewards import level_for_xp, task_xp, update_streak

DEFAULT_PATH = Path("data/state.json")


@dataclass
class Goal:
    id: int
    title: str


@dataclass
class Task:
    id: int
    goal_id: int | None
    title: str
    due: str                # ISO date
    difficulty: int = 1
    kind: str = "normal"    # "normal" | "boss"
    done: bool = False


@dataclass
class State:
    goals: list[Goal] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    xp: int = 0
    points: int = 0
    streak: int = 0
    last_done: str | None = None
    inventory: list[dict] = field(default_factory=list)   # asdict(Item)
    equipped: dict = field(default_factory=dict)          # slot -> item name
    next_id: int = 1

    def new_id(self) -> int:
        n = self.next_id
        self.next_id += 1
        return n


def data_path() -> Path:
    return Path(os.environ.get("JARVIS_DATA", DEFAULT_PATH))


def load(path: Path | None = None) -> State:
    path = path or data_path()
    if not path.exists():
        return State()
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["goals"] = [Goal(**g) for g in raw.get("goals", [])]
    raw["tasks"] = [Task(**t) for t in raw.get("tasks", [])]
    return State(**raw)


def save(state: State, path: Path | None = None) -> None:
    path = path or data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(path)


def add_goal(state: State, title: str) -> Goal:
    goal = Goal(state.new_id(), title)
    state.goals.append(goal)
    return goal


def add_task(state: State, title: str, due: date, difficulty: int = 1,
             goal_id: int | None = None, kind: str = "normal") -> Task:
    if difficulty not in (1, 2, 3):
        raise ValueError("difficulty must be 1, 2 or 3")
    task = Task(state.new_id(), goal_id, title, due.isoformat(), difficulty, kind)
    state.tasks.append(task)
    return task


def complete_task(state: State, task_id: int, today: date) -> dict:
    """Mark a task done and apply rewards. Returns a summary dict."""
    task = next((t for t in state.tasks if t.id == task_id), None)
    if task is None:
        raise KeyError(f"no task with id {task_id}")
    if task.done:
        raise ValueError("task is already completed")

    last = date.fromisoformat(state.last_done) if state.last_done else None
    old_level = level_for_xp(state.xp)
    state.streak = update_streak(last, state.streak, today)
    gained = task_xp(task.difficulty, state.streak, boss=task.kind == "boss")

    task.done = True
    state.last_done = today.isoformat()
    state.xp += gained
    state.points += gained
    new_level = level_for_xp(state.xp)
    return {"xp": gained, "streak": state.streak,
            "level": new_level, "leveled_up": new_level > old_level}
