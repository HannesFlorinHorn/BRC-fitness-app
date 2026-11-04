# Roadmap

Last updated: 2026-11-04. Current milestone: **1.1**.

Goal: the training season has already started, so the first priority is a small, reliable app that collects data. Everything fancy comes later.

How to use this file: work on the current milestone only, tick items off when done, and record changes of direction in the decisions log at the bottom.

## Milestone 1.1: build the core app (local)

Goal: login, record a session, review history, running on the owner's machine.

- [ ] Create the repo, Django project (`config/`) and app (`training/`), `requirements.txt`, `.env.example`, `.gitignore` (including `.env`, `db.sqlite3`, backups)
- [x] Models and migrations: custom User (email login), Category (= plan), Exercise (with method 1/2, plan position, active flag), Session, SessionExercise, ExerciseSet (UUID keys)
- [x] Admin: all models registered, exercise catalog editable, sessions viewable by staff
- [ ] Seed data: categories (legs, arms, core) and the real exercise list with each exercise's Methode (ask the owner for the list once the models exist)
- [ ] Login and logout pages, login required for everything else
- [ ] Pages: start session from a plan (legs/arms/core preloads its exercises) or mixed, add exercise from catalog, swap exercise order, add sets (prefilled from the previous set), delete last set, finish (skipped exercises are dropped)
- [ ] Pages: history list and session detail (own data only)
- [ ] Design tokens from `docs/design/DESIGN.md` applied via `custom.css` on top of Pico.css
- [ ] Tests: permission test (athlete A vs B), a model test, and one test of the full logging flow

Done when: a full session can be recorded and found again in the history, and the permission test passes.

## Milestone 1.2: run locally, test and debug

Goal: find the problems on your own machine before any server exists.

- [ ] Run from a clean clone using only the commands in `CLAUDE.md`
- [ ] Create 2-3 test athletes and one coach in the admin; log several realistic sessions
- [ ] Open the app on a real phone over the local network (`runserver 0.0.0.0:8000`, add your computer's LAN address to `ALLOWED_HOSTS`) in Safari and Chrome; fix layout and usability problems
- [ ] Check login persistence on the phone (session stays valid across days; cookie lifetime set deliberately)
- [ ] Confirm test accounts cannot see each other's data by trying direct URLs
- [ ] Back up with `sqlite3 ... ".backup"`, delete the database, restore from the backup and check that the data is back
- [ ] Short bug list written down and cleared

Done when: you have logged real-looking sessions on your phone without surprises and a restore has worked.

## Milestone 1.3: go live for the group

Goal: colleagues can reach it over HTTPS and start logging.

- [ ] Production settings from the environment: `DEBUG` off, strong `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, secure cookies, proxy header setting
- [ ] Gunicorn (few workers; SQLite allows one writer at a time) and WhiteNoise for static files
- [ ] Docker Compose with Caddy and the app, database file and backups on a volume
- [ ] Small EU VPS, domain, DNS, firewall, SSH keys only, automatic security updates
- [ ] Nightly SQLite backup copied off the server; restore tested once
- [ ] Accounts created for colleagues, a one-page "how to log in" note, consent for storing their data

Done when: every colleague has logged in on their phone and a nightly backup exists off the server.

## Milestone 2: make it useful

- [ ] Progress charts: estimated 1RM per exercise, weekly volume, personal records
- [ ] Coach overview page (athletes, last session, consistency) instead of the admin
- [ ] Edit and delete sessions, exercise catalog page, CSV export
- [ ] Training plan logic for Methode 1 and 2: target reps per set and suggested weight progression (rules to be written down by the owner first)
- [ ] More tests, especially for permissions

## Milestone 3: phone polish

- [ ] Better logging screens (steppers, rest timer, keep screen awake)
- [ ] Optional Home Screen shortcut
- [ ] Draft of the running session kept locally and uploaded when online
- [ ] Only if needed: API layer (Django REST Framework) and a React frontend

## Milestone 4: Raspberry Pi

- [ ] Same Compose setup on a Pi with an SSD (not an SD card), Ethernet, Cloudflare Tunnel as the front door
- [ ] Move the SQLite file, check data, keep the VPS for a week as fallback

## Milestone 5: extras

- [ ] Notifications, personal records history, further design polish, whatever the group asks for

## Decisions log

- 2026-11-04: Django with server-rendered pages for the first milestones. No API or JavaScript framework until Milestone 3 and only if needed.
- 2026-11-04: **SQLite instead of Postgres.** Tiny data volume, one file to back up and move to the Pi. Backups use `sqlite3 .backup`.
- 2026-11-04: Browser only, no installed app. Login uses Django's server-set session cookie, never a token in browser storage. Email + password, accounts created by the owner.
- 2026-11-04: Milestone 1 split into 1.1 build, 1.2 local testing, 1.3 live deployment.
- 2026-11-04: Design drafted in Google Stitch and handed over via `docs/design/DESIGN.md` plus screenshots.
- 2026-11-04: UI language is **English**.
- 2026-11-04: Custom user model with **email as login**, created before the first migration.
- 2026-11-04: **Methode is fixed per exercise** (`Exercise.method`, 1 or 2), not chosen per session. Milestone 1 only stores it; the plan logic it drives comes later.
- 2026-11-05: `SessionExercise.method` stores a snapshot of the exercise's Methode at logging time, so history stays correct if the coach changes an exercise's Methode.
- 2026-11-04: Sessions have no title. They are labelled by their categories.
- 2026-11-05: **Categories are the training plans** (fixed templates, editable by the coach in the admin). Starting a session from a plan preloads its active exercises in order; athletes may add exercises from other plans and swap the order. `Session.categories` was removed: a session's categories are derived from its exercises.
- Open: exact rules of Methode 1 and 2.
