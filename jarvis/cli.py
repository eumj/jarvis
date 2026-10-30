"""Command line interface: python -m jarvis.cli <command>"""
import argparse
from datetime import date, timedelta

from jarvis import models, planner
from jarvis.rewards import level_for_xp, xp_for_level


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jarvis", description="자기계발 보상 에이전트")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("add-goal", help="목표 추가")
    g.add_argument("title")

    t = sub.add_parser("add-task", help="과제 추가")
    t.add_argument("title")
    t.add_argument("--due", default=None, help="YYYY-MM-DD (기본: 오늘)")
    t.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3])
    t.add_argument("--goal", type=int, default=None, help="목표 번호")
    t.add_argument("--boss", action="store_true", help="보스 스테이지 과제")

    pl = sub.add_parser("plan", help="LLM으로 목표를 날짜별 과제로 분할")
    pl.add_argument("goal")
    pl.add_argument("--days", type=int, default=7)

    sub.add_parser("today", help="오늘 할 일")

    d = sub.add_parser("done", help="과제 완료")
    d.add_argument("task_id", type=int)

    sub.add_parser("status", help="레벨/XP/streak 확인")
    return p


def run(argv: list[str], today: date | None = None, complete=None) -> int:
    args = build_parser().parse_args(argv)
    today = today or date.today()
    state = models.load()

    try:
        if args.cmd == "add-goal":
            goal = models.add_goal(state, args.title)
            print(f"목표 #{goal.id} 추가: {goal.title}")
        elif args.cmd == "add-task":
            due = date.fromisoformat(args.due) if args.due else today
            task = models.add_task(state, args.title, due, args.difficulty,
                                   args.goal, "boss" if args.boss else "normal")
            print(f"과제 #{task.id} 추가 ({task.due}, 난이도 {task.difficulty})")
        elif args.cmd == "plan":
            items = planner.generate_plan(args.goal, args.days, complete=complete)
            goal = models.add_goal(state, args.goal)
            for item, due in planner.schedule(items, today):
                models.add_task(state, item.title, due, item.difficulty, goal.id)
            bosses = planner.boss_days(args.days)
            for day in bosses:
                topics = [i.title for i in items if i.day <= day]
                title = planner.generate_boss_title(args.goal, day, topics, complete)
                models.add_task(state, title, today + timedelta(days=day - 1),
                                3, goal.id, kind="boss")
            print(f"목표 #{goal.id} '{goal.title}': 과제 {len(items)}개와 "
                  f"보스 {len(bosses)}개를 {args.days}일에 배치했습니다.")
        elif args.cmd == "today":
            tasks = [t for t in state.tasks
                     if t.due <= today.isoformat() and not t.done]
            if not tasks:
                print("오늘 남은 과제가 없습니다.")
            for t in tasks:
                mark = "[BOSS] " if t.kind == "boss" else ""
                print(f"#{t.id} {mark}{t.title} (난이도 {t.difficulty}, 기한 {t.due})")
        elif args.cmd == "done":
            r = models.complete_task(state, args.task_id, today)
            print(f"완료! +{r['xp']} XP, 연속 {r['streak']}일, 레벨 {r['level']}")
            if r["bonus_points"]:
                print(f"보스 클리어! 보너스 +{r['bonus_points']} 포인트")
            if r["leveled_up"]:
                print("레벨 업!")
        elif args.cmd == "status":
            lv = level_for_xp(state.xp)
            print(f"레벨 {lv} | XP {state.xp} (다음 레벨까지 "
                  f"{xp_for_level(lv + 1) - state.xp}) | 포인트 {state.points} "
                  f"| 연속 {state.streak}일")
    except planner.PlannerError as e:
        print(f"오류: {e}")
        return 1
    except (KeyError, ValueError) as e:
        print(f"오류: {e.args[0] if e.args else e}")
        return 1

    models.save(state)
    return 0


def main() -> None:
    raise SystemExit(run(__import__("sys").argv[1:]))


if __name__ == "__main__":
    main()
