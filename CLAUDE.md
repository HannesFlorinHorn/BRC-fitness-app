# Training Tracker

Small Django web app for a training group (about 10 people). Athletes log training sessions (exercises, sets, weight, reps) in their phone browser and review their history. The coach can see everyone's data. The app collects real data during the season, so protecting that data matters more than adding features.

## Read first

- `ROADMAP.md`: current milestone, task checklist and decisions log. Work only on the current milestone. Tick items off when they are done and add new decisions to the log.
- `docs/design/DESIGN.md`: design tokens and rules exported from Google Stitch (colors, fonts, spacing). Read it before touching any template or CSS. Screen mockups (HTML from Stitch, German placeholder text) are in `docs/design/screen_exploration/`. They show more than Milestone 1.1 needs; build only what the current milestone lists.

## Stack (Milestone 1)

- Python + Django, server-rendered pages (Django templates and forms). No separate API and no JavaScript framework.
- Database: **SQLite** (one file, `db.sqlite3`, never committed to Git).
- Login: Django's built-in auth with a custom user model (`accounts.User`, email as the login field, no username). Accounts are created by the owner in the Django admin. No signup page and no email sending.
- Styling: Pico.css (a single CSS file) plus a small `static/css/custom.css` that applies the design tokens. No JS build step.
- Settings via environment variables (`.env`, gitignored; keep `.env.example` up to date).
- Later (not now): Gunicorn, WhiteNoise, Caddy, Docker Compose, VPS, Raspberry Pi. See `ROADMAP.md`.

## Out of scope until the roadmap says so

Django REST Framework, React, Vite, TypeScript, Tailwind build, service worker, offline sync, PWA install features, charts, Postgres, Docker, hosting. If a task seems to need one of these, stop and ask.

## Data model

All primary keys of Session, SessionExercise and ExerciseSet are UUIDs (cheap now, and it prevents duplicate uploads if offline sync is added later).

- `User` (custom, in `accounts`): email is the login field. Created before the first migration so it never has to be swapped later.
- `Category`: name (seed data: legs, arms, core). Each category is also a **training plan**: its active exercises in `position` order are the template a new session starts from. The coach edits plans in the admin (category page).
- `Exercise` (catalog): name (unique), category, method (1 or 2), position (order within its plan), is_active. Logged exercises are never deleted; the coach deactivates them instead. Managed in the admin. Athletes pick from this list rather than typing free text, so progress data stays clean. The method is fixed per exercise and set by the owner/coach; athletes never choose it.
- `Session`: athlete (FK to user), date, notes, created_at, finished_at (empty while the session is still running). No stored categories and no title: the label is derived from the categories of its exercises (e.g. "Legs · Arms").
- `SessionExercise`: session, exercise, order (athletes may swap it), method. `method` is a snapshot copied automatically from the exercise when it is logged (never chosen by the athlete), so changing a catalog exercise's Methode does not rewrite past sessions.
- `ExerciseSet`: session_exercise, number, weight_kg (decimal), reps (positive integer)

Do not name a model `Set` (it clashes with Python's `set`).

## Roles and permissions

- Athlete: sees and edits only their own sessions. Every athlete-facing query must filter by `request.user`. Never fetch a Session, SessionExercise or ExerciseSet by id alone.
- Coach: staff user. In Milestone 1 the coach reads everything through the Django admin. No coach pages yet.
- The coach is read-only in athlete pages. Only the owner changes roles, in the admin.
- Keep at least one automated test proving that athlete A cannot read, edit or delete athlete B's data (page and direct-URL access). Run it before every commit.

## Commands

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver            # http://127.0.0.1:8000
python manage.py runserver 0.0.0.0:8000   # to test from a phone on the same Wi-Fi
pytest
python manage.py makemigrations --check   # must pass before committing
```

SQLite backup (safe while the app runs): `sqlite3 db.sqlite3 ".backup 'backup.sqlite3'"`. Do not copy the file with `cp` while the app is running.

## Rules for working in this repo

- Make a short plan before larger changes, then work in small steps. Commit after each working step with a clear message.
- Run `pytest` and `makemigrations --check` before saying a task is done.
- Never edit an existing migration after it was applied to data that matters. Add a new one.
- Ask before adding any dependency. Keep `requirements.txt` pinned.
- Never commit secrets, `.env`, `db.sqlite3` or backups.
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and cookie security flags all come from the environment. Defaults must be safe for production, and local development overrides them in `.env`.
- Mobile first: design for a 390 px wide phone, one-handed use, tap targets of at least 48 px, number inputs with `inputmode="decimal"` for weight and `inputmode="numeric"` for reps.
- Starting a session: the athlete picks a plan (legs, arms, core), which preloads its exercises, or "mixed", which starts empty. Exercises from any plan can be added and the order swapped. Finishing removes preloaded exercises without sets. The logic lives in `training/services.py`.
- Logging flow: after each saved set, show the form again prefilled with the previous set's weight and reps.
- Keep the UI simple. A boring page that works beats a clever one.

## Methode

Every exercise is either Methode 1 or Methode 2. The Methode defines the training plan logic: how many reps per set the athlete must reach and how the weight changes across sets and sessions. In Milestone 1 the app only stores the Methode on the exercise. Targets and progression come later, once the owner has written down the rules.

## UI language

English for all UI text, code, comments and commits.

## Open questions (ask the owner, do not guess)

1. The exact rules of Methode 1 and Methode 2 (target reps per set, weight progression). Not needed before the training plan milestone.
