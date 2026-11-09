# Strength Progression Rules (Method 1 and 2)

Nov 9, 2026 · @Hannes-Florin Horn

Rules from the coach's sheet "Belastungssteuerung im Krafttraining" (Phase 2: Kraftaufbau). One change for this group: Method 2 uses **10‑13‑15** reps instead of 15‑18‑20. Every exercise must be done cleanly: no compensating movements, no momentum, no joint pain.

## Method 1: 2 (3) max sets

For limbs, main and multi-joint exercises.

| Set | Reps | Weight |
| --- | --- | --- |
| 1 (warm-up) | 10 | 50 % of Set 3 |
| 2 (warm-up) | 5 | 75 % of Set 3 |
| 3 | max | working weight |
| 4 | max | from Set 3 reps via Table A |
| 5 (optional) | max | from Set 4 reps via Table A |

- Set 3 reps → **Table A** → Set 4 weight.
- Set 4 reps → **Table B** → Set 3 weight in the next session.
- Set 5 is never used to set the next session's weight.

| Reps | Table A: change for Set 4 (5) | Table B: change for next session |
| --- | --- | --- |
| ≤ 2 | ↓↓ −2.5 to −5 kg | ↓ −2.5 to −5 kg |
| 3–4 | ↓ 0 to −2.5 kg | = same |
| 5–6 | = same | ↑ +2.5 to +5 kg |
| 7–10 | ↑ +2.5 to +5 kg | ↑↑ +2.5 to +7.5 kg |
| ≥ 11 | ↑↑ +5 to +10 kg | ↑↑↑ +5 to +10 kg |

Examples from the sheet (weight Set 3/Set 4, reps Set 3/Set 4):

| Session 1 | Session 2 |
| --- | --- |
| 20/25 kg, 9/5 reps | 30 kg (↑) |
| 20/20 kg, 6/4 reps | 20 kg (=) |
| 20/20 kg, 5/2 reps | 17.5 kg (↓) |

**Deload: every 4th week.** Set 1: 10 reps and Set 2: 5 reps, same as the week before. Sets 3 and 4: 5 reps at the Set 2 weight, no max effort. (The week plan for KW 48 writes this as Set 1 50 %, Set 2 75 %, Sets 3+4 −30 %.)

## Method 2: rep progression 10‑13‑15

For core and accessory exercises.

- Start with 10 reps in all 3 sets, at a moderate weight (RPE 4).
- Each next session: first set +3 or +2 reps (10 → 13 → 15), the other sets with the same reps.
- If that fails, the next session starts with the same reps as before.
- Only when all 3 sets reach 15 reps: weight +2.5 to 5 kg, and the cycle starts again at 10.

Example (sheet's example, converted to 10‑13‑15):

| Session | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Weight (kg) | 25 | 25 | 25 | 30 | 30 | 30 | 30 | 35 |
| Reps | 10/10/10 | 13/13/13 | 15/15/15 | 10/10/10 | 13/13/13 | 15/13/10 | 15/15/15 | 10/10/10 |
| Sets | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |

Session 6 failed, so session 7 repeats the same target.

**Deload: after 2–3 complete cycles.** Weights about −30 %, 15 reps, one set fewer per exercise.

## How the app applies these rules

Decided with the owner on 2026-11-09. The app **suggests**; athletes always log what they actually did.

- Ranges in the tables ("+2.5 to +5 kg"): the app suggests the **lower end**, i.e. the smaller change, and shows the range as a hint.
- Weights are rounded **down** to **2.5 kg** steps (the smallest plate step).
- Method 1: the next session's working weight (Set 3) is the **Set 4 weight** of the last session, changed by Table B using the **Set 4 reps**. Nothing else counts.
- Method 2: one target for all 3 sets (10, 13, 15) at one weight. When the athlete saves the first set, the plan of the day (target reps and target weight) is stored with the exercise. The next session depends **only on the last session**, its plan and its sets. The rows are checked top to bottom; the first match wins:

  | # | Last session | Next session |
  | --- | --- | --- |
  | 1 | A set with fewer than 10 reps | target one step down (15 → 13, 13 → 10); already at 10: weight −2.5 kg, target 10 |
  | 2 | A set lighter than the target weight | same target, same weight |
  | 3 | All 3 sets with 15 reps or more | weight +2.5 kg, target 10 (whatever the target was) |
  | 4 | All 3 sets reach the target | next target (10 → 13 → 15), same weight |
  | 5 | Anything else (fewer reps, fewer than 3 sets) | same target, same weight |

  Heavier sets count, but the next weight stays at the target weight. The first time, no weight is suggested; the lowest of the logged weights then counts as the target weight. Sessions logged before plans were stored (no plan): the lowest weight counts, and the weakest set sets the target (below 10: −2.5 kg and 10; 10 or more: 13; 13 or more: 15; 15 or more in all 3 sets: +2.5 kg and 10).
- Method 1 warm-ups: the **first time** an exercise is logged, the athlete logs Sets 1 and 2 themselves (the info box gives about 50 % and 75 % of the working weight as a guide). Once there is an earlier session with at least 3 sets, the warm-ups are logged automatically when the athlete saves the working set (Set 3), from its weight. An exercise that is skipped therefore has no sets and is dropped at Finish.
- Method 1 without a Set 4 last time: the working weight stays at the last Set 3 weight.
- Exercises without a Methode keep the simple behaviour: the form is prefilled with the previous set.
- Deload weeks (both Methods) are **not** in the app yet; they come in Milestone 2.
