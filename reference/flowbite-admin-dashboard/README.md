# Flowbite Admin Dashboard — local reference (do not deploy as-is)

Source: [themesberg/flowbite-admin-dashboard](https://github.com/themesberg/flowbite-admin-dashboard), MIT License (see `LICENSE`). Downloaded 2026-08-07.

## Why this folder exists

A 7B-class local model cannot reliably fetch external URLs at generation time. `mini_framework.json` → `design_system.reference_template` points to this project as the structural/visual reference for our Twig templates — these are the actual source files, saved locally so the AI never needs to (and never should try to) download anything from GitHub itself.

## What these files are — and are NOT

These are **Hugo template sources** (`{{ ... }}` is Go template syntax, not Twig), kept only as a **structural and Tailwind-class reference**:

- `layouts/partials/sidebar.html` — sidebar nav structure, accordion pattern (`data-collapse-toggle`)
- `layouts/partials/navbar-dashboard.html` — top navbar structure
- `layouts/partials/footer-dashboard.html` — footer structure
- `layouts/_default/baseof.html`, `layouts/_default/dashboard.html` — page shell composition
- `content/crud/users.html`, `content/crud/products.html` — CRUD list page markup
- `content/authentication/sign-in.html` — login page markup
- `content/_index.html` — dashboard homepage (charts/widgets/stat cards)

**DO NOT copy-paste these files directly into `resources/views/`.** Every time this reference is used:

1. Strip all `{{ ... }}` Hugo/Go template expressions — they mean nothing in Twig.
2. Replace `dark:*` classes — this project has dark mode OFF (see `design_system.dark_mode`).
3. Replace their default gray/blue theme with this project's tokens (see `design_system.tokens` — `green-800` brand, etc.), NOT their colors.
4. Re-express dynamic parts using our actual data: the sidebar becomes the generic `menu`-driven renderer in `canonical_snippets.menu_registry_pattern`, NOT this file's Hugo loop.
5. Follow `rules/ui_templates.md` for the already-adapted, Twig-ready versions of these patterns — that file is the authoritative one to generate from. This folder is what `ui_templates.md` was itself adapted from, kept for when a *new* pattern (not yet covered in `ui_templates.md`) needs a structural reference.
