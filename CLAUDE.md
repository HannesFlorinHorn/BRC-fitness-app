# Training Tracker

Small Django web app for a training group (about 10 people). Athletes log training sessions (exercises, sets, weight, reps) in their phone browser and review their history. The coach can see everyone's data. The app collects real data during the season, so protecting that data matters more than adding features.

## Read first

- `ROADMAP.md`: current milestone, task checklist and decisions log. Work only on the current milestone. Tick items off when they are done and add new decisions to the log.
- `docs/METHODE_RULES.md`: the rules of Methode 1 and 2 and how the app applies them. Read it before touching `training/methode.py` or the sets page.
- `docs/design/DESIGN.md`: design tokens and rules exported from Google Stitch (colors, fonts, spacing). Read it before touching any template or CSS. Screen mockups (HTML from Stitch, German placeholder text) are in `docs/design/screen_exploration/`. They show more than Milestone 1.1 needs; build only what the current milestone lists.

## Stack (Milestone 1)

- Python + Django, server-rendered pages (Django templates and forms). No separate API and no JavaScript framework.
- Database: **SQLite** (one file, `db.sqlite3`, never committed to Git; `DATABASE_PATH` moves it, e.g. onto the Docker volume). WAL mode, so `db.sqlite3-wal` and `db.sqlite3-shm` belong to it.
- Login: Django's built-in auth with a custom user model (`accounts.User`, email as the login field, no username). Accounts are created by the owner in the Django admin. No signup page and no email sending.
- Styling: Pico.css (a single CSS file) plus a small `static/css/custom.css` that applies the design tokens. No JS build step.
- Static files: WhiteNoise serves them with DEBUG off, from `staticfiles/` (fingerprinted names). Run `collectstatic` before every start with DEBUG off, or every page fails with "Missing staticfiles manifest entry".
- Settings via environment variables (`.env`, gitignored; keep `.env.example` up to date).
- Later (not now): Gunicorn, Caddy, Docker Compose, VPS, Raspberry Pi. See `ROADMAP.md`.

## Out of scope until the roadmap says so

Django REST Framework, React, Vite, TypeScript, Tailwind build, service worker, offline sync, PWA install features, charts, Postgres, Docker, hosting. If a task seems to need one of these, stop and ask.

## Data model

All primary keys of Session, SessionExercise and ExerciseSet are UUIDs (cheap now, and it prevents duplicate uploads if offline sync is added later).

- `User` (custom, in `accounts`): email is the login field. Created before the first migration so it never has to be swapped later.
- `Category`: name (seed data: legs, arms, core). The muscle group of an exercise; used to label sessions and group the exercise picker. Not a plan.
- `Exercise` (catalog): name (unique), category, method (1, 2 or empty when no Methode applies), tracking (`sets` = weight × reps, `check` = tick when done, e.g. Planks, Abs), is_active. Logged exercises are never deleted; the coach deactivates them instead. Managed in the admin. Athletes pick from this list rather than typing free text, so progress data stays clean. The method is fixed per exercise and set by the owner/coach; athletes never choose it.
- `Plan` (session template): name, owner (FK to user; empty = club plan), is_active. Club plans (seed: Legs, Arms, Core) are maintained by the coach in the admin; athletes can build their own. Read plans with `Plan.objects.visible_to(user)` and edit only `Plan.objects.owned_by(user)`.
- `PlanExercise`: plan, exercise, position. The same exercise can appear in any number of plans.
- `Session`: athlete (FK to user), date, notes, created_at, finished_at (empty while the session is still running). No stored categories and no title: the label is derived from the categories of its exercises (e.g. "Legs · Arms").
- `SessionExercise`: session, exercise, order (athletes may swap it), method, is_done (ticked by the athlete for `check` exercises; ticked automatically for Methode exercises after Set 4 (Methode 1) or Set 3 (Methode 2), unticked if a set is deleted below that; exercises without a Methode are never marked done). `method` is a snapshot copied automatically from the exercise when it is logged (never chosen by the athlete), so changing a catalog exercise's Methode does not rewrite past sessions. For Methode 2, `target_reps` and `target_weight` store the plan of the day when the first set is saved (also never chosen by the athlete); the next session is worked out from it.
- `ExerciseSet`: session_exercise, number, weight_kg (decimal), reps (positive integer)

Do not name a model `Set` (it clashes with Python's `set`).

## Roles and permissions

- Athlete: sees and edits only their own sessions. Every athlete-facing query must filter by `request.user`. Never fetch a Session, SessionExercise, ExerciseSet or Plan by id alone. Athletes can read club plans but not change them.
- Coach: has two accounts. A normal athlete account for their own training, and a staff account that reads everything through the Django admin. No coach pages yet.
- Staff accounts are read-only in athlete pages: they cannot start or log sessions. Only the owner changes roles, in the admin.
- Keep at least one automated test proving that athlete A cannot read, edit or delete athlete B's data (page and direct-URL access). Run it before every commit.

## Commands

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver            # http://127.0.0.1:8000
python manage.py runserver 0.0.0.0:8000   # to test from a phone on the same Wi-Fi
python manage.py collectstatic --noinput   # before running with DEBUG=false
pytest
python manage.py makemigrations --check   # must pass before committing
```

SQLite backup (safe while the app runs): `sqlite3 db.sqlite3 ".backup 'backup.sqlite3'"`. Do not copy the file with `cp` while the app is running: in WAL mode the latest saves can still be in `db.sqlite3-wal`.

Logs: warnings and errors (server errors, Methode fallbacks, security warnings) go to the console: the `runserver` terminal locally, `docker compose logs` later. 404s are not logged.

## Rules for working in this repo

- Make a short plan before larger changes, then work in small steps. Commit after each working step with a clear message.
- Run `pytest` and `makemigrations --check` before saying a task is done.
- Never edit an existing migration after it was applied to data that matters. Add a new one.
- Ask before adding any dependency. Keep `requirements.txt` pinned.
- Never commit secrets, `.env`, `db.sqlite3` or backups.
- Logins expire after inactivity: 30 minutes for staff accounts, 7 days for athletes, restarted by every request (`accounts/session_lifetime.py`, `STAFF_SESSION_AGE` and `SESSION_COOKIE_AGE` in settings).
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, the cookie security flags and `SECURE_SSL_REDIRECT` all come from the environment. Defaults must be safe for production, and local development overrides them in `.env`. With `DEBUG` off the app refuses to start with a weak `SECRET_KEY`. Django trusts Caddy's `X-Forwarded-Proto` header, so Gunicorn must never be reachable except through Caddy. `config/tests.py` runs `check --deploy` with production values.
- Mobile first: design for a 390 px wide phone, one-handed use, tap targets of at least 48 px, number inputs with `inputmode="decimal"` for weight and `inputmode="numeric"` for reps.
- Starting a session: the athlete picks a plan (club or their own), which preloads its active exercises in plan order, or "free", which starts empty. Exercises from any plan can be added and the order swapped. Finishing removes preloaded exercises that have no sets and are not ticked. `check` exercises get a tick, never sets. The logic lives in `training/services.py`.
- A session's date is prefilled with today and can be set to a past date (never a future one) to log a session already done.
- Each athlete has at most one open session (enforced by a database constraint). An open session finishes itself 26 hours after it was started, with its end time recorded as start + 3 hours; with no background job, this happens on the athlete's next visit (`get_open_session`). A session with nothing logged is discarded when it finishes.
- Logging flow: after each saved set, show the form again prefilled. Exercises with a Methode are prefilled with the suggestion from `training/methode.py` (calculated from the logged sets, nothing stored); for Methode 1 the athlete enters the working set first and the two warm-ups are logged with it (the first time an exercise is logged, the athlete logs the warm-ups too). Exercises without a Methode repeat the previous set's weight and reps.
- Keep the UI simple. A boring page that works beats a clever one.

## Methode

Most exercises are Methode 1 or Methode 2; some (e.g. Planks, Abs) have none. The Methode defines the training plan logic: how many reps per set the athlete must reach and how the weight changes across sets and sessions. The rules are written down in `docs/METHODE_RULES.md`; the app suggests targets and weights from them (Milestone 1.2). Deload weeks come in Milestone 2.

## UI language

English for all UI text, code, comments and commits. Exception: the legal notice and privacy pages (`templates/legal/`) are in German.

## Open questions (ask the owner, do not guess)

1. Deload weeks for Methode 1 and 2: which weight applies (Set 2 weight or −30 %) and how deload weeks are chosen (marked by the coach or counted automatically). Milestone 2.
