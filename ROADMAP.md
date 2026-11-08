# Roadmap

Last updated: 2026-11-08. Current milestone: **1.2**.

Goal: the training season has already started, so the first priority is a small, reliable app that collects data. Everything fancy comes later.

How to use this file: work on the current milestone only, tick items off when done, and record changes of direction in the decisions log at the bottom.

## Milestone 1.1: build the core app (local)

Goal: login, record a session, review history, running on the owner's machine.

- [x] Create the repo, Django project (`config/`) and app (`training/`), `requirements.txt`, `.env.example`, `.gitignore` (including `.env`, `db.sqlite3`, backups)
- [x] Models and migrations: custom User (email login), Category, Exercise (with method 1/2, active flag), Plan + PlanExercise, Session, SessionExercise, ExerciseSet (UUID keys)
- [x] Admin: all models registered, exercise catalog editable, sessions viewable by staff
- [x] Seed data: categories (legs, arms, core), club plans (Legs, Arms, Core) and the real exercise list with each exercise's Methode and plan order (ask the owner for the list)
- [x] Login and logout pages, login required for everything else
- [x] Pages: start session from a plan (preloads its exercises) or free, add exercise from catalog, swap exercise order, add sets (prefilled from the previous set), tick "check" exercises as done, delete last set, finish (skipped exercises are dropped)
- [x] Pages: history list and session detail (own data only)
- [x] Design tokens from `docs/design/DESIGN.md` applied via `custom.css` on top of Pico.css
- [x] Tests: permission test (athlete A vs B), a model test, and one test of the full logging flow

Done when: a full session can be recorded and found again in the history, and the permission test passes.

## Milestone 1.2: run locally, test and debug

Goal: find the problems on your own machine before any server exists.

- [ ] Run from a clean clone using only the commands in `CLAUDE.md`
- [ ] Create 2-3 test athletes and one coach in the admin; log several realistic sessions
- [ ] Open the app on a real phone over the local network (`runserver 0.0.0.0:8000`, add your computer's LAN address to `ALLOWED_HOSTS`) in Safari and Chrome; fix layout and usability problems
- [ ] Check login persistence on the phone (session stays valid across days; cookie lifetime set deliberately)
- [ ] Confirm test accounts cannot see each other's data by trying direct URLs
- [ ] Back up with `sqlite3 ... ".backup"`, delete the database, restore from the backup and check that the data is back
- [ ] Simple landing page (details to be agreed with the owner)
- [ ] Register mechanism (details to be agreed with the owner; `CLAUDE.md` currently says no signup page)
- [ ] Feedback field (details to be agreed with the owner)
- [ ] Legal pages and texts (details to be agreed with the owner)
- [ ] Consider dropping Pico.css (keeping only `custom.css`) if overriding its styles keeps causing trouble during phone testing
- [ ] Short bug list written down and cleared

Bug list:

- [x] Email login is case-sensitive: `Anna@club.de` and `anna@club.de` count as different accounts. Until fixed, create accounts in lowercase.
- [ ] Session lifetimes: admin sessions last 30 minutes, athlete sessions 7 days. Both restart with every request. Admin and app share one cookie, so this needs a small piece of custom code, not just settings; to be planned with the owner.
- [x] Auto-finish rule change: an open session closes automatically after 26 hours instead of 4. When auto-closed, its end time is stored as start + 3 hours. Update `CLAUDE.md` and the tests with it.
- [ ] Friendly error pages: styled `404.html`, `403.html` and `500.html` with a way back to the history. Typing the address of an action (e.g. `/finish/`) leads back to the related page instead of an empty 405 page.
- [ ] Each exercise at most once per session. The exercise picker lists only exercises not yet in the session, and adding checks it again on the server (a stale page or double tap must not create a duplicate). To decide when planning: a database rule as well, and what happens when a plan contains the same exercise twice.
- [x] Adding an exercise always redirects to the session log (today, weight exercises go straight to their sets page).
- [ ] History lists sessions in the order they were logged. To decide when planning: newest or oldest first, and where a backdated session goes (today the list sorts by training date).
- [ ] Session log shows which exercises are still open: open ones use the active card style (red border), done ones have their name greyed out a little. To decide when planning: when a weight exercise counts as done (after its first set, or only when the athlete marks it).

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
- [ ] "My plans" page: athletes create their own plans, add and reorder exercises (model exists since 1.1; until then plans are created in the admin)
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
- 2026-11-05: **Plans are their own model**, replacing "categories are plans" from earlier the same day. Club plans have no owner and are edited by the coach in the admin; athletes can own private plans. An exercise can be in several plans. Category is only the muscle group again.
- 2026-11-05: Club plans seeded: Legs (Mon), Arms (Wed), Core (Fri), 14 exercises. **Methode is optional** (Planks, Abs have none). Exercises are tracked either as weight × reps or as **tick when done** (Planks, Abs). Variants (plank sides, shoulder directions) are one entry each; athletes know what to do.
- 2026-11-06: Session date is prefilled with today and may be changed to a past date, so a session already done can be logged.
- 2026-11-06: **One open session per athlete.** It finishes itself 4 hours after it was started, on the athlete's next visit. Sessions with nothing logged are discarded.
- 2026-11-06: The coach has **two accounts**: a normal athlete account to train with and a staff account to see everyone's data in the admin. Staff accounts cannot log sessions.
- 2026-11-06: In `DESIGN.md`, the color list at the top wins over the text below it (red `#ba0022`, light background). Pico.css and the fonts are stored in `static/`, so pages load nothing from Google or a CDN.
- 2026-11-06: An exercise's `tracking` never changes between sets and check once logged, so it is not copied per session like the Methode. Session labels stay derived from current categories and are not stored.
- 2026-11-08: An open session now finishes itself **26 hours** after it was started (was 4), so a session can be finished the next morning. The auto-finished end time is recorded as start + 3 hours.
- Open: exact rules of Methode 1 and 2.
- 2026-11-05: The athlete page for building own plans moves to **Milestone 2**. Until then, plans are created in the admin.
