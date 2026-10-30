"""Progress review: completion rate, miss patterns and load suggestions."""
from datetime import date, timedelta

from jarvis.models import State
from jarvis.rewards import level_for_xp

LOW_RATE = 0.4      # below this, suggest fewer / easier tasks
HIGH_RATE = 0.9     # at or above this, suggest harder tasks
MIN_MISSES = 2      # misses on one weekday before we call it a pattern
WEEKDAYS = "월화수목금토일"


def build_report(state: State, today: date, days: int = 7) -> dict:
    """Stats over tasks due in the last `days` days (today included)."""
    if days < 1:
        raise ValueError("days must be >= 1")
    first = (today - timedelta(days=days - 1)).isoformat()
    due = [t for t in state.tasks if first <= t.due <= today.isoformat()]
    done = [t for t in due if t.done]
    rate = len(done) / len(due) if due else None

    missed_by_day: dict[int, int] = {}
    for t in due:
        if not t.done:
            wd = date.fromisoformat(t.due).weekday()
            missed_by_day[wd] = missed_by_day.get(wd, 0) + 1
    worst = max(missed_by_day.items(), key=lambda kv: kv[1], default=None)
    worst_day = WEEKDAYS[worst[0]] if worst and worst[1] >= MIN_MISSES else None

    by_difficulty = {}
    for d in (1, 2, 3):
        group = [t for t in due if t.difficulty == d]
        if group:
            by_difficulty[d] = sum(t.done for t in group) / len(group)

    return {
        "days": days, "due": len(due), "done": len(done), "rate": rate,
        "worst_day": worst_day, "by_difficulty": by_difficulty,
        "bosses_cleared": sum(1 for t in state.tasks if t.kind == "boss" and t.done),
        "level": level_for_xp(state.xp), "xp": state.xp, "streak": state.streak,
        "suggestion": suggest(rate),
    }


def suggest(rate: float | None) -> str:
    """Advice only; the user decides whether to change anything."""
    if rate is None:
        return "아직 기한이 지난 과제가 없습니다."
    if rate < LOW_RATE:
        return "달성률이 낮습니다. 하루 과제 수를 줄이거나 쉬운 과제부터 시작해 보세요."
    if rate >= HIGH_RATE:
        return "아주 잘하고 있습니다. 난이도를 한 단계 올려 보는 건 어떨까요?"
    return "좋은 페이스입니다. 지금 과제량을 유지하세요."


def format_report(r: dict) -> str:
    lines = [f"[최근 {r['days']}일 리포트]"]
    if r["rate"] is None:
        lines.append("달성률: 기한이 지난 과제 없음")
    else:
        lines.append(f"달성률: {r['done']}/{r['due']} ({r['rate']:.0%})")
    for d, rate in r["by_difficulty"].items():
        lines.append(f"  난이도 {d}: {rate:.0%}")
    if r["worst_day"]:
        lines.append(f"자주 못 한 요일: {r['worst_day']}요일")
    lines.append(f"레벨 {r['level']} | XP {r['xp']} | 연속 {r['streak']}일 "
                 f"| 보스 클리어 {r['bosses_cleared']}회")
    lines.append(f"제안: {r['suggestion']}")
    return "\n".join(lines)
