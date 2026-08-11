---
name: wvictory
description: Generate or modify code in the wVictory spec repo — a PHP 8.2 / Slim 4 / Eloquent / Twig / Tailwind admin-app generator. Use when scaffolding the starter boilerplate, adding or changing a CRUD module (migration, model, service, controller, routes, views, sidebar menu, RBAC permissions), fixing a bug in a generated app, or editing mini_framework.json / starter_boilerplate_blueprint.json themselves. Triggers on "modul", "CRUD", "migration", "boilerplate", "sidebar menu", "RBAC", "canonical snippet", "gotcha", or any mention of mini_framework / PROJECT_BRAIN.
---

# wVictory

This repo is a **spec generator**, not an app. Application code is generated *into* this
directory from `mini_framework.json`. If `app/`, `routes/`, or `resources/` do not exist,
the project is still empty — run the onboarding question first (see "New project" below).

## Read the spec in slices, not whole

`mini_framework.json` is ~86 KB (~22k tokens). **Do not read it in full.** `tools/spec.py`
prints one focused slice at a time:

```bash
python tools/spec.py map          # the 10 steps + which snippet each one needs
python tools/spec.py rules        # non-negotiable rules + design tokens
python tools/spec.py step 7       # one pipeline step in full
python tools/spec.py show <key>   # one canonical snippet, verbatim
python tools/spec.py gotcha       # the 16 bugs that already happened
python tools/spec.py grep <text>  # find which slice mentions something
```

Read `rules/ui_templates.md` when writing Twig, and `PROJECT_BRAIN.json` to see what
already exists. `reference/flowbite-admin-dashboard/` is a *structural* reference only —
it is Hugo, not Twig, and its gray/dark theme is not ours.

## Three flows

### New project (no `app/` yet)
Ask the user first — this is mandatory, do not assume:

> Proyek ini masih baru/kosong. Mau inisialisasi Starter Skeleton Boilerplate dulu
> (Auth, Login, Profile, Base Layout, Sidebar, Navbar), atau langsung buat modul?

Then follow `starter_boilerplate_blueprint.json`. `composer.json` is created **first**,
copied verbatim from `python tools/spec.py show composer_json_template`, before anything else.

### New or changed module
Follow all 10 steps from `python tools/spec.py map`, **in order**. The two most commonly
skipped are step 2 (permission seeder) and step 10 (menu entry) — skip either and the
module exists but nobody can reach it.

For each step: run `python tools/spec.py step <n>`, then `show` whichever snippets it
names, and copy them **verbatim**.

### Bug in a generated app
Fix the **canonical snippet**, not just the generated file — otherwise the next
generation reintroduces it. Then add a `verified_gotchas` entry (symptom, root cause,
fix) and, if you can express it as a check, add one to `eval/run.py` so it can never
come back silently.

## Rules that are not style preferences

Each of these exists because a real generation broke. Full list: `python tools/spec.py rules`.

- **Slim 4, not Laravel.** No `View::` / `DB::` / `Validator::`, no `Illuminate\Http\Request`,
  no `FormRequest`. Controllers take `ServerRequestInterface` / `ResponseInterface`.
- **Copy verbatim.** Anything in `canonical_snippets` is copied, never retyped from memory.
  Retyping from memory is the direct cause of most entries in `verified_gotchas`.
- **Constructor and call site travel together.** For any class you `new` by hand (every
  middleware in `routes/web.php`), take the class *and* its instantiation line from the
  same snippet, in the same step.
- **No external fetch.** Never curl/wget/download during generation. Frontend assets are
  already in `public/assets/vendor/`. If something looks missing, say so — do not fetch it.
- **Hooks are write-once.** If `app/Hooks/{Model}Hooks.php` exists, do not touch it, ever,
  unless the user explicitly asks to edit that file. Human business logic lives there and
  regenerating the Service must never destroy it.
- **No placeholders.** No `// TODO`, no empty method bodies.
- **Dark mode is off.** Do not emit `dark:` classes.

## Finish every task with these two

1. **Update `PROJECT_BRAIN.json`** — `current_state.last_feature`, `last_migration`,
   `last_updated`, `modules_completed`, `known_issues_log`. Use the existing schema, do
   not invent a new one. This is part of "done", not an extra. Never wait to be reminded.

2. **Run the regression suite:**

```bash
python eval/run.py
```

Every `FAIL` is a bug the spec already knows about — the message names the
`verified_gotchas` entry. A green run on the `app` tier means the 16 known
failure modes are all absent. `python eval/run.py --coverage` shows which gotchas
are guarded by a check.
