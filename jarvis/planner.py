"""Split a goal into dated tasks with the Claude API."""
import json
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta

MODEL = "claude-sonnet-5-5"
MAX_ITEMS = 60

PROMPT = """사용자의 자기계발 목표를 {days}일 안에 실행할 수 있는 작은 과제로 나눠 주세요.
목표: {goal}

규칙:
- 과제 하나는 하루 안에 끝낼 수 있어야 합니다.
- JSON 배열만 출력하세요. 설명이나 코드블록은 쓰지 마세요.
- 각 원소: {{"title": 문자열, "difficulty": 1~3 정수, "day": 1~{days} 정수}}
- day는 몇 번째 날에 할 일인지를 뜻합니다. 쉬운 것부터 어려운 것 순서로 배치하세요."""


class PlannerError(Exception):
    pass


@dataclass
class PlanItem:
    title: str
    difficulty: int
    day: int


def parse_plan(text: str, days: int) -> list[PlanItem]:
    """Validate the model's reply. Raises PlannerError on any problem."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        raise PlannerError("응답에서 JSON 배열을 찾지 못했습니다.")
    try:
        raw = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise PlannerError(f"JSON 형식 오류: {e}") from e
    if not raw or len(raw) > MAX_ITEMS:
        raise PlannerError(f"과제 수가 비정상입니다 ({len(raw)}개).")
    items = []
    for r in raw:
        try:
            title = str(r["title"]).strip()
            difficulty, day = int(r["difficulty"]), int(r["day"])
        except (KeyError, TypeError, ValueError) as e:
            raise PlannerError(f"과제 항목 형식 오류: {r!r}") from e
        if not title or difficulty not in (1, 2, 3) or not 1 <= day <= days:
            raise PlannerError(f"값이 범위를 벗어났습니다: {r!r}")
        items.append(PlanItem(title, difficulty, day))
    return items


def schedule(items: list[PlanItem], start: date) -> list[tuple[PlanItem, date]]:
    """Day N maps to start + (N-1) days. Dates are decided by code, not the model."""
    return [(i, start + timedelta(days=i.day - 1)) for i in items]


def _default_client():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise PlannerError(
            "ANTHROPIC_API_KEY가 없습니다. .env.example을 .env로 복사해 키를 넣어 주세요.")
    import anthropic
    return anthropic.Anthropic()


def generate_plan(goal: str, days: int, client=None, retries: int = 1) -> list[PlanItem]:
    if not goal.strip():
        raise PlannerError("목표가 비어 있습니다.")
    if not 1 <= days <= 90:
        raise PlannerError("기간은 1~90일 사이여야 합니다.")
    client = client or _default_client()
    last_error = None
    for _ in range(retries + 1):
        try:
            reply = client.messages.create(
                model=MODEL, max_tokens=2000,
                messages=[{"role": "user",
                           "content": PROMPT.format(goal=goal, days=days)}])
        except PlannerError:
            raise
        except Exception as e:  # network/auth errors from the SDK
            raise PlannerError(f"API 호출 실패: {e}") from e
        text = "".join(b.text for b in reply.content if getattr(b, "text", None))
        try:
            return parse_plan(text, days)
        except PlannerError as e:
            last_error = e
    raise PlannerError(f"계획 생성 실패 (재시도 후에도): {last_error}")
