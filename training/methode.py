"""Suggestions for Methode 1 and 2, following docs/METHODE_RULES.md.

The app suggests and never enforces: athletes log what they actually did.
Nothing here is stored; every suggestion is worked out from the sets the
athlete has logged. The functions below the database part only take lists
of (weight, reps) pairs, so they can be tested against the coach's sheet.
"""

import logging
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, Decimal
from typing import NamedTuple

from .models import Exercise, SessionExercise

logger = logging.getLogger(__name__)

PLATE_STEP = Decimal("2.5")


class Step(NamedTuple):
    min_reps: int
    max_reps: int | None  # None = "or more"
    change: Decimal  # what the app suggests: the smaller change of the range
    up_to: Decimal  # the other end of the range, shown as a hint


# Methode 1, Set 3 reps -> change for Set 4 (and Set 4 reps -> Set 5).
TABLE_A = (
    Step(0, 2, Decimal("-2.5"), Decimal("-5")),
    Step(3, 4, Decimal("0"), Decimal("-2.5")),
    Step(5, 6, Decimal("0"), Decimal("0")),
    Step(7, 10, Decimal("2.5"), Decimal("5")),
    Step(11, None, Decimal("5"), Decimal("10")),
)

# Methode 1, Set 4 reps -> change for the next session's working weight (Set 3).
TABLE_B = (
    Step(0, 2, Decimal("-2.5"), Decimal("-5")),
    Step(3, 4, Decimal("0"), Decimal("0")),
    Step(5, 6, Decimal("2.5"), Decimal("5")),
    Step(7, 10, Decimal("2.5"), Decimal("7.5")),
    Step(11, None, Decimal("5"), Decimal("10")),
)

# Methode 1 warm-ups: (reps, share of the working weight).
WARM_UPS = ((10, Decimal("0.5")), (5, Decimal("0.75")))

# Methode 2: target reps for all 3 sets; after the last one the weight goes up.
TARGETS = (10, 13, 15)
METHOD_2_SETS = 3
METHOD_2_WEIGHT_STEP = Step(0, None, Decimal("2.5"), Decimal("5"))


@dataclass
class PlannedSet:
    """An upcoming set, shown greyed out below the logged ones."""

    number: int
    note: str
    weight: Decimal | None = None
    reps: int | None = None  # None = as many as possible

    @property
    def weight_display(self):
        return plain(self.weight) if self.weight is not None else None


@dataclass
class Guide:
    """What the sets page shows for the next set."""

    lines: list[str] = field(default_factory=list)  # the message box
    planned: list[PlannedSet] = field(default_factory=list)
    next: PlannedSet | None = None  # the set the form is for
    weight: Decimal | None = None  # prefilled in the form
    reps: int | None = None

    def prefill(self, today):
        """Prefill with the next planned set, or else repeat the last logged set."""
        if self.next is not None:
            self.weight, self.reps = self.next.weight, self.next.reps
        elif today:
            self.weight, self.reps = today[-1]


def guide_for(logged):
    """The guide for a logged exercise, or None if it has no Methode. If a
    calculation fails, the page falls back to repeating the last set."""
    if logged.method is None or logged.exercise.tracking != Exercise.Tracking.SETS:
        return None
    try:
        return calculate_guide(logged)
    except Exception:
        logger.exception("Methode guide failed for logged exercise %s", logged.pk)
        return None


def calculate_guide(logged):
    today = [(s.weight_kg, s.reps) for s in logged.sets.all()]
    if logged.method == Exercise.Method.METHOD_1:
        history = [[(s.weight_kg, s.reps) for s in earlier.sets.all()] for earlier in earlier_sessions(logged)]
        return method_1_guide(history, today)
    return method_2_guide(method_2_last_session(logged), today, stored_plan(logged))


def stored_plan(logged):
    if logged.target_reps is None:
        return None
    last = method_2_last_session(logged)
    return Method2Plan(logged.target_reps, logged.target_weight, method_2_today(last).change if last else None)


def logs_warm_ups_itself(logged):
    """Methode 1 warm-ups are logged with the working set once the exercise
    has a full earlier session; the first time, the athlete logs them."""
    if logged.method != Exercise.Method.METHOD_1:
        return False
    return any(len(earlier.sets.all()) >= 3 for earlier in earlier_sessions(logged))


def earlier_sessions(logged):
    """The athlete's earlier logs of this exercise under the same Methode, oldest first."""
    session = logged.session
    return (
        SessionExercise.objects.filter(
            session__athlete_id=session.athlete_id, exercise_id=logged.exercise_id, method=logged.method
        )
        .exclude(session=session)
        .filter(session__date__lte=session.date)
        .order_by("session__date", "session__created_at")
        .prefetch_related("sets")
    )


# Building blocks


def round_down(weight):
    """Down to the next plate step, never below 0."""
    return max((weight / PLATE_STEP).to_integral_value(ROUND_FLOOR) * PLATE_STEP, Decimal("0"))


def look_up(table, reps):
    """The row of the table whose rep range contains reps."""
    for step in table:
        if reps >= step.min_reps and (step.max_reps is None or reps <= step.max_reps):
            return step
    raise ValueError(f"No row for {reps} reps")


def apply(weight, step):
    return round_down(weight + step.change)


def plain(weight):
    """62.5, 60: the weight without trailing zeros."""
    return f"{weight:.2f}".rstrip("0").rstrip(".")


def kg(weight):
    return f"{plain(weight)} kg"


def signed(change):
    if change == 0:
        return "same"
    return ("+" if change > 0 else "−") + kg(abs(change))


def change_text(step):
    """"+2.5 kg, up to +5 kg" or just "same"."""
    if step.up_to == step.change:
        return signed(step.change)
    return f"{signed(step.change)}, up to {signed(step.up_to)}"


def warm_ups(working_weight):
    """The two warm-up sets for a working weight, as (weight, reps)."""
    return [(round_down(working_weight * share), reps) for reps, share in WARM_UPS]


# Methode 1: 2 warm-ups, Set 3 max reps, Set 4 (and optional 5) adjusted by Table A.

METHOD_1_INTRO = [
    "No sessions yet:",
    "Set 1 · warm-up · 10 reps · about 50 % of your working weight",
    "Set 2 · warm-up · 5 reps · about 75 % of your working weight",
    "Set 3 · working set · target 5–6 reps",
    "Set 4/5 · adjusted automatically",
    "This time you log the warm-ups yourself; from the next session on they are calculated.",
]


def method_1_working_weight(last):
    """Today's working weight from the last session: Set 4 via Table B, else Set 3 unchanged."""
    if len(last) >= 4:
        step = look_up(TABLE_B, last[3][1])
        return apply(last[3][0], step), change_text(step)
    return round_down(last[2][0]), "same as last Set 3"


def method_1_guide(history, today):
    guide = Guide()
    done = [sets for sets in history if len(sets) >= 3]
    working = None
    if done:
        last = done[-1]
        summary = f"Last time: Set 3 · {kg(last[2][0])} × {last[2][1]}"
        if len(last) >= 4:
            summary += f" · Set 4 · {kg(last[3][0])} × {last[3][1]}"
        working, how = method_1_working_weight(last)
        guide.lines += [summary, f"Today's working weight: {kg(working)} ({how})"]
    elif len(today) < 3:
        guide.lines += METHOD_1_INTRO

    if len(today) >= 3:
        working = today[2][0]
        set_4 = look_up(TABLE_A, today[2][1])
        guide.lines.append(f"Set 3: {today[2][1]} reps → Set 4: {kg(apply(working, set_4))} ({change_text(set_4)})")
    if len(today) >= 4:
        weight, reps = today[3]
        set_5 = look_up(TABLE_A, reps)
        next_session = look_up(TABLE_B, reps)
        guide.lines.append(f"Set 4: {reps} reps → Set 5 (optional): {kg(apply(weight, set_5))} ({change_text(set_5)})")
        guide.lines.append(f"Next session: Set 3 at {kg(apply(weight, next_session))} ({change_text(next_session)})")

    guide.planned, guide.next = method_1_planned(today, working, known=bool(done))
    guide.prefill(today)
    return guide


def method_1_planned(today, working, known):
    """The sets still to come, and the one the form is for. Once the working
    weight is known from an earlier session, the athlete's first entry is
    Set 3 and the warm-ups are logged with it (services.add_set). The first
    time, the athlete logs the warm-ups first."""
    count = len(today)
    set_3 = PlannedSet(3, "working set · max reps", working)
    set_4 = PlannedSet(4, "adjusted after Set 3 · max reps")
    if count == 0 and known:
        planned = [
            PlannedSet(number, "warm-up · logged with Set 3", weight, reps)
            for number, (weight, reps) in enumerate(warm_ups(working), start=1)
        ]
        return planned + [set_3, set_4], set_3
    if count == 0:
        set_1 = PlannedSet(1, "warm-up · about 50 % of your working weight", reps=WARM_UPS[0][0])
        set_2 = PlannedSet(2, "warm-up · about 75 % of your working weight", reps=WARM_UPS[1][0])
        return [set_1, set_2, set_3, set_4], set_1
    if count == 1:
        weight = warm_ups(working)[1][0] if working is not None else None
        set_2 = PlannedSet(2, "warm-up · about 75 % of your working weight", weight, WARM_UPS[1][0])
        return [set_2, set_3, set_4], set_2
    if count == 2:
        return [set_3, set_4], set_3
    if count == 3:
        set_4.note, set_4.weight = "max reps", apply(today[2][0], look_up(TABLE_A, today[2][1]))
        return [set_4], set_4
    if count == 4:
        set_5 = PlannedSet(5, "optional · max reps", apply(today[3][0], look_up(TABLE_A, today[3][1])))
        return [set_5], set_5
    return [], None


# Methode 2: 3 sets with one target (10, 13, 15); after 15 the weight goes up.
# The plan of the day (target reps and weight) is stored with the first set,
# so the next session depends only on the last one: its plan and its sets.

METHOD_2_MIN_REPS = 10  # a set below this: the target goes one step down


@dataclass
class Method2Plan:
    target: int = TARGETS[0]
    weight: Decimal | None = None  # None: first time, the athlete picks it
    change: Step | None = None  # weight change against the last session, for the info box


@dataclass
class LastSession:
    sets: list
    target: int | None  # None: logged before plans were stored
    weight: Decimal | None


RAISE = METHOD_2_WEIGHT_STEP
LOWER = Step(0, None, -METHOD_2_WEIGHT_STEP.change, -METHOD_2_WEIGHT_STEP.change)


def method_2_next(last):
    """The plan for the next session, and a short verdict on the last one.
    The rows are checked top to bottom (docs/METHODE_RULES.md). Any case the
    rules do not cover keeps the plan of the last session."""
    sets = last.sets[:METHOD_2_SETS]
    if not sets:
        return Method2Plan(last.target or TARGETS[0], last.weight), "no sets"
    weights = [w for w, _ in sets]
    reps = [r for _, r in sets]

    if last.weight is None:
        # First session (or logged before plans were stored): nothing was planned.
        start = [w for w, r in last.sets if r >= METHOD_2_MIN_REPS]
        if start:
            return Method2Plan(TARGETS[0], round_down(max(start))), "first session"
        return Method2Plan(TARGETS[-1], apply(min(weights), LOWER), LOWER), f"no set with {METHOD_2_MIN_REPS} reps"

    target = last.target if last.target in TARGETS else TARGETS[0]
    same_plan = Method2Plan(target, round_down(last.weight))
    if len(sets) < METHOD_2_SETS:
        return same_plan, "fewer than 3 sets"
    if len(set(weights)) > 1:
        return same_plan, "different weights, plan kept"

    weight = weights[0]  # the weight the athlete used in all 3 sets
    if all(r < METHOD_2_MIN_REPS for r in reps):
        return Method2Plan(TARGETS[-1], apply(weight, LOWER), LOWER), f"all sets below {METHOD_2_MIN_REPS} reps"
    if min(reps) < METHOD_2_MIN_REPS:
        lower = TARGETS[max(TARGETS.index(target) - 1, 0)]
        return Method2Plan(lower, round_down(weight)), f"a set below {METHOD_2_MIN_REPS} reps"
    if min(reps) >= TARGETS[-1]:
        return Method2Plan(TARGETS[0], apply(weight, RAISE), RAISE), f"{TARGETS[-1]} reps reached"
    # One step above the highest target all 3 sets reached, never below the current one.
    reached = max(t for t in TARGETS if t <= min(reps))
    verdict = f"target {target} {'reached' if min(reps) >= target else 'not reached'}"
    return Method2Plan(max(next_target(reached), target), round_down(weight)), verdict


def next_target(target):
    return TARGETS[min(TARGETS.index(target) + 1, len(TARGETS) - 1)]


def method_2_today(last):
    """Today's plan from the last session, or the starting plan the first time."""
    if last is None:
        return Method2Plan()
    return method_2_next(last)[0]


def method_2_plan_to_store(logged):
    """The plan stored with the first set; the starting plan if the calculation fails."""
    try:
        return method_2_today(method_2_last_session(logged))
    except Exception:
        logger.exception("Methode 2 plan failed for logged exercise %s", logged.pk)
        return Method2Plan()


def method_2_last_session(logged):
    """The most recent earlier log of this exercise that has sets."""
    for earlier in reversed(list(earlier_sessions(logged))):
        sets = [(s.weight_kg, s.reps) for s in earlier.sets.all()]
        if sets:
            return LastSession(sets, earlier.target_reps, earlier.target_weight)
    return None


def method_2_guide(last, today, stored=None):
    """stored: today's plan once the first set is saved (it wins over a recalculation)."""
    guide = Guide()
    plan = stored or method_2_today(last)
    if last is None:
        guide.lines.append(f"No sessions yet: {METHOD_2_SETS} sets × {TARGETS[0]} reps at a moderate weight.")
    else:
        verdict = method_2_next(last)[1]
        weights = [w for w, _ in last.sets]
        weight_text = kg(weights[0]) if len(set(weights)) == 1 else " / ".join(plain(w) for w in weights) + " kg"
        reps = " / ".join(str(r) for _, r in last.sets)
        guide.lines.append(f"Last time: {weight_text} · {reps} ({verdict})")
    if plan.weight is not None:
        today_text = f"Today: {METHOD_2_SETS} sets × {plan.target} reps at {kg(plan.weight)}"
        if plan.change is not None:
            today_text += f" ({change_text(plan.change)})"
        guide.lines.append(today_text)

    if len(today) >= METHOD_2_SETS:
        upcoming = method_2_next(LastSession(today, plan.target, plan.weight))[0]
        guide.lines.append(f"Next session: {METHOD_2_SETS} × {upcoming.target} reps at {kg(upcoming.weight)}")

    weight = today[-1][0] if today else plan.weight
    guide.planned = [
        PlannedSet(number, f"target {plan.target} reps", weight, plan.target)
        for number in range(len(today) + 1, METHOD_2_SETS + 1)
    ]
    guide.next = guide.planned[0] if guide.planned else None
    guide.prefill(today)
    return guide
