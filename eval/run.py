#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wVictory eval harness — turns the spec's verified_gotchas into a regression suite.

Usage:
    python eval/run.py                  # check the spec + whatever app exists here
    python eval/run.py --target DIR     # check a project generated somewhere else
    python eval/run.py --tier spec      # spec | app | runtime | all (default: all)
    python eval/run.py --coverage       # which verified_gotchas have a guarding check
    python eval/run.py --json           # machine-readable output

Exit code is 1 if any check FAILs, 0 otherwise. SKIP never fails the run.

Three tiers:
    spec     — validates this repo (JSON well-formed, every canonical snippet
               actually compiles, referenced assets exist). Always runnable.
    app      — static checks on a GENERATED project. Auto-skipped when the app
               has not been generated yet. This is the regression suite: each
               check names the verified_gotchas key it guards.
    runtime  — needs `composer install` (and, for the HTTP checks, a database).
               Auto-skipped with a reason when prerequisites are missing.

Adding a check: write a function decorated with @check(...) and give it the
`gotcha=` key it guards. `--coverage` will then stop reporting that gotcha as
unguarded. Stdlib only, no dependencies.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


# ---------------------------------------------------------------------------
# check registry
# ---------------------------------------------------------------------------

@dataclass
class Result:
    status: str
    detail: str = ""
    items: list = field(default_factory=list)


CHECKS = []


def check(tier, cid, desc, gotcha=None):
    def deco(fn):
        fn.tier, fn.cid, fn.desc, fn.gotcha = tier, cid, desc, gotcha
        CHECKS.append(fn)
        return fn
    return deco


def ok(detail=""):
    return Result(PASS, detail)


def bad(detail, items=None):
    return Result(FAIL, detail, items or [])


def skip(detail):
    return Result(SKIP, detail)


# ---------------------------------------------------------------------------
# context / helpers
# ---------------------------------------------------------------------------

class Ctx:
    def __init__(self, target):
        self.target = os.path.abspath(target)
        self._spec = None
        self._files = None

    def path(self, *parts):
        return os.path.join(self.target, *parts)

    def exists(self, *parts):
        return os.path.exists(self.path(*parts))

    def read(self, *parts):
        p = self.path(*parts)
        if not os.path.exists(p):
            return None
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()

    @property
    def spec(self):
        if self._spec is None:
            raw = self.read("mini_framework.json")
            self._spec = json.loads(raw) if raw else {}
        return self._spec

    def walk(self, subdir, ext):
        """All files under target/subdir with the given extension."""
        root = self.path(subdir)
        out = []
        if not os.path.isdir(root):
            return out
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ("vendor", "node_modules", ".git")]
            for fn in filenames:
                if fn.endswith(ext):
                    out.append(os.path.join(dirpath, fn))
        return out

    def app_php(self):
        out = []
        for sub in ("app", "routes", "bin", "config", "database"):
            out += self.walk(sub, ".php")
        for extra in ("public/index.php",):
            if self.exists(*extra.split("/")):
                out.append(self.path(*extra.split("/")))
        return out

    def views(self):
        return self.walk("resources/views", ".twig")

    def has_app(self):
        return self.exists("composer.json") and os.path.isdir(self.path("app"))

    def rel(self, p):
        try:
            return os.path.relpath(p, self.target).replace("\\", "/")
        except ValueError:
            return p


def read_text(p):
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def grep(paths, pattern, flags=0):
    """[(relpath, lineno, line)] for every line matching pattern."""
    rx = re.compile(pattern, flags)
    hits = []
    for p in paths:
        for i, line in enumerate(read_text(p).splitlines(), 1):
            if rx.search(line):
                hits.append((p, i, line.strip()))
    return hits


def strip_comments(src):
    """Crude PHP/Twig comment stripper so checks don't match prose in comments."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    src = re.sub(r"^[ \t]*(//|#)[^\n]*$", "", src, flags=re.M)
    return src


PHP = shutil.which("php")
COMPOSER = shutil.which("composer") or shutil.which("composer.bat")


def php_lint(code):
    """(ok, message) — run `php -l` over a code string."""
    if not PHP:
        return None, "php not on PATH"
    fd, tmp = tempfile.mkstemp(suffix=".php")
    try:
        with io.open(fd, "w", encoding="utf-8") as fh:
            fh.write(code)
        proc = subprocess.run([PHP, "-l", tmp], capture_output=True, text=True)
        if proc.returncode == 0:
            return True, ""
        msg = (proc.stdout + proc.stderr).replace(tmp, "<snippet>").strip()
        return False, msg.splitlines()[0] if msg else "lint failed"
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def iter_snippets(spec):
    """Yield (dotted_path, code, target_path) for every canonical_snippets .code."""
    def rec(node, path, inherited_target):
        if not isinstance(node, dict):
            return
        tp = node.get("target_path", inherited_target)
        if isinstance(node.get("code"), str):
            yield path, node["code"], tp
        for k, v in node.items():
            if k not in ("code", "target_path") and isinstance(v, dict):
                yield from rec(v, path + "." + k if path else k, tp)
    yield from rec(spec.get("canonical_snippets", {}), "", None)


def deplaceholder(code):
    """Turn spec placeholders like {ModelName} into plain identifiers so php -l can
    parse a template. Deliberately does NOT touch PHP interpolation ({$var}, ${x})."""
    return re.sub(r"\{([A-Za-z][A-Za-z0-9_]*)\}", r"\1", code)


def classify_snippet(code, target_path):
    """'php_file' | 'php_fragment' | 'php_member' | 'twig' | 'json' | 'unknown'"""
    head = code.lstrip()
    tp = (target_path or "").lower()
    if head.startswith("<?php"):
        return "php_file"
    if ".twig" in tp or head.startswith(("{%", "{{", "<thead", "<form", "<div")):
        return "twig"
    if "composer.json" in tp or (head.startswith("{") and '"require"' in code):
        return "json"
    if re.match(r"^(public|private|protected|final|abstract|static)\s|^function\s", head):
        return "php_member"
    if head.startswith(("$", "return ", "use ", "if (", "foreach ")):
        return "php_fragment"
    return "unknown"


# ===========================================================================
# TIER: spec — validates this repo itself. Always runnable.
# ===========================================================================

@check("spec", "spec.json_valid", "Spec JSON files parse")
def c_json_valid(ctx):
    broken = []
    for name in ("mini_framework.json", "starter_boilerplate_blueprint.json", "PROJECT_BRAIN.json"):
        raw = ctx.read(name)
        if raw is None:
            broken.append(f"{name}: missing")
            continue
        try:
            json.loads(raw)
        except Exception as exc:
            broken.append(f"{name}: {exc}")
    return bad(f"{len(broken)} spec file(s) invalid", broken) if broken else ok("3 files parse")


@check("spec", "spec.brain_schema", "PROJECT_BRAIN.json matches project_brain_protocol.schema_example")
def c_brain_schema(ctx):
    raw = ctx.read("PROJECT_BRAIN.json")
    if raw is None:
        return bad("PROJECT_BRAIN.json missing — the brain-evolve protocol has nothing to update")
    brain = json.loads(raw)
    example = ctx.spec.get("project_brain_protocol", {}).get("schema_example", {})
    missing = [k for k in example if k not in brain]
    if missing:
        return bad("keys missing vs schema_example", missing)
    sub = [k for k in example.get("current_state", {}) if k not in brain.get("current_state", {})]
    if sub:
        return bad("current_state keys missing", sub)
    return ok(f"{len(example)} top-level keys present")


@check("spec", "spec.agent_loader", "Agent loader chain resolves to exactly one procedure file")
def c_agent_loader(ctx):
    problems = []
    skill = "/".join((".claude", "skills", "wvictory", "SKILL.md"))
    agents = ctx.read("AGENTS.md")
    if agents is None:
        problems.append("AGENTS.md missing — nothing auto-loads for any agent")
    elif "SKILL.md" not in agents:
        problems.append("AGENTS.md does not point at the skill; the procedure has forked")
    if not ctx.exists(*skill.split("/")):
        problems.append(f"{skill} missing — AGENTS.md points at a dead path")
    else:
        body = ctx.read(*skill.split("/"))
        if not body.startswith("---") or "name:" not in body.split("---")[1]:
            problems.append("SKILL.md has no YAML frontmatter; Claude Code will not load it")
    for name in ("CLAUDE.md", "GEMINI.md"):
        body = ctx.read(name)
        if body is None:
            problems.append(f"{name} missing")
        elif "AGENTS.md" not in body:
            problems.append(f"{name} does not point at AGENTS.md (duplicate source of truth)")

    # VS Code's built-in chat: always-on instructions + the /wvictory prompt file.
    for name in (".github/copilot-instructions.md", ".github/prompts/wvictory.prompt.md"):
        body = ctx.read(*name.split("/"))
        if body is None:
            problems.append(f"{name} missing")
        elif "SKILL.md" not in body:
            problems.append(f"{name} does not point at the skill; the procedure has forked")
    prompt = ctx.read(".github", "prompts", "wvictory.prompt.md")
    if prompt is not None and not prompt.startswith("---"):
        problems.append(".github/prompts/wvictory.prompt.md has no frontmatter; /wvictory will not register")

    return bad(f"{len(problems)} problem(s)", problems) if problems else ok(
        "5 loaders -> SKILL.md (single procedure)")


@check("spec", "spec.snippets_php_lint", "Every PHP canonical_snippet compiles (php -l)")
def c_snippets_lint(ctx):
    if not PHP:
        return skip("php not on PATH")
    failures, linted, skipped = [], 0, 0
    for path, code, tp in iter_snippets(ctx.spec):
        kind = classify_snippet(code, tp)
        body = deplaceholder(code)
        if kind == "php_file":
            wrapped = body
        elif kind == "php_member":
            wrapped = "<?php\nclass __Probe {\n" + body + "\n}\n"
        elif kind == "php_fragment":
            wrapped = "<?php\n" + body + "\n"
        else:
            skipped += 1
            continue
        good, msg = php_lint(wrapped)
        linted += 1
        if good is False:
            failures.append(f"canonical_snippets.{path}  ({kind}) -> {msg}")
    if failures:
        return bad(f"{len(failures)}/{linted} snippet(s) do not compile", failures)
    return ok(f"{linted} PHP snippets compile ({skipped} non-PHP skipped)")


@check("spec", "spec.snippets_json_valid", "JSON canonical_snippets parse (composer.json template)")
def c_snippets_json(ctx):
    failures, n = [], 0
    for path, code, tp in iter_snippets(ctx.spec):
        if classify_snippet(code, tp) != "json":
            continue
        n += 1
        try:
            json.loads(code)
        except Exception as exc:
            failures.append(f"canonical_snippets{path}: {exc}")
    if not n:
        return skip("no JSON snippets found")
    return bad(f"{len(failures)}/{n} invalid", failures) if failures else ok(f"{n} JSON snippet(s) parse")


@check("spec", "spec.snippets_twig_balanced", "Twig canonical_snippets have balanced delimiters")
def c_snippets_twig(ctx):
    failures, n = [], 0
    for path, code, tp in iter_snippets(ctx.spec):
        if classify_snippet(code, tp) != "twig":
            continue
        n += 1
        for open_d, close_d in (("{%", "%}"), ("{{", "}}")):
            if code.count(open_d) != code.count(close_d):
                failures.append(
                    f"canonical_snippets{path}: {code.count(open_d)}x '{open_d}' vs {code.count(close_d)}x '{close_d}'")
    if not n:
        return skip("no Twig snippets found")
    return bad(f"{len(failures)} imbalance(s)", failures) if failures else ok(f"{n} Twig snippet(s) balanced")


@check("spec", "spec.vendor_assets_present", "Pre-provisioned vendor assets exist (NO_EXTERNAL_FETCH)")
def c_vendor_assets(ctx):
    required = [
        "public/assets/vendor/css/tailwind.min.css",
        "public/assets/vendor/css/flowbite.min.css",
        "public/assets/vendor/css/sweetalert2.min.css",
        "public/assets/vendor/css/choices.min.css",
        "public/assets/vendor/css/flatpickr.min.css",
        "public/assets/vendor/css/fonts.css",
        "public/assets/vendor/js/axios.min.js",
        "public/assets/vendor/js/sweetalert2.all.min.js",
        "public/assets/vendor/js/choices.min.js",
        "public/assets/vendor/js/flatpickr.min.js",
        "public/assets/vendor/js/flowbite.min.js",
        "public/assets/vendor/js/app.js",
        "public/assets/vendor/fonts/Inter-Variable.woff2",
    ]
    missing = [p for p in required if not ctx.exists(*p.split("/"))]
    if missing:
        return bad(f"{len(missing)} asset(s) missing — generation would be tempted to fetch", missing)
    return ok(f"{len(required)} assets present")


@check("spec", "spec.app_js_sidebar_toggle", "Pre-provisioned app.js still exposes initSidebarToggle()",
       gotcha="app_shell_not_responsive")
def c_app_js(ctx):
    body = ctx.read("public", "assets", "vendor", "js", "app.js")
    if body is None:
        return bad("public/assets/vendor/js/app.js missing")
    if "initSidebarToggle" not in body:
        return bad("initSidebarToggle() not found — the mobile drawer has no JS behind it")
    for token in ("sidebar-toggle", "sidebar-backdrop"):
        if token not in body:
            return bad(f"app.js does not reference #{token}; markup ids and JS have drifted apart")
    return ok("initSidebarToggle + both element ids referenced")


@check("spec", "spec.reference_local", "Design reference is stored locally, not fetched")
def c_reference(ctx):
    if not os.path.isdir(ctx.path("reference", "flowbite-admin-dashboard")):
        return bad("reference/flowbite-admin-dashboard/ missing — design_system points at a dead path")
    if not ctx.exists("reference", "flowbite-admin-dashboard", "LICENSE"):
        return bad("reference kept without its LICENSE file (MIT requires it)")
    return ok("reference present with LICENSE")


# ===========================================================================
# TIER: app — static regression checks on a GENERATED project.
# Each check guards a specific verified_gotchas entry.
# ===========================================================================

def _need_app(ctx):
    if not ctx.has_app():
        return skip("no generated app (composer.json + app/ not found)")
    return None


@check("app", "app.structure", "Blueprint's mandatory files exist")
def c_structure(ctx):
    g = _need_app(ctx)
    if g:
        return g
    required = [
        "composer.json", "public/index.php", "bin/setup.php", "app/bootstrap.php",
        "app/menu.php", "routes/web.php",
        "app/Middleware/AuthMiddleware.php", "app/Middleware/RbacMiddleware.php",
        "app/Middleware/CsrfViewMiddleware.php", "app/Middleware/RateLimitMiddleware.php",
        "app/Controllers/AuthController.php", "app/Controllers/ProfileController.php",
        "app/Controllers/DashboardController.php",
        "resources/views/layouts/base.twig", "resources/views/partials/navbar.twig",
        "resources/views/partials/sidebar.twig", "resources/views/auth/login.twig",
        "resources/views/profile/index.twig", "resources/views/profile/password.twig",
    ]
    missing = [p for p in required if not ctx.exists(*p.split("/"))]
    return bad(f"{len(missing)} required file(s) missing", missing) if missing else ok(
        f"all {len(required)} present")


@check("app", "app.php_syntax", "Every generated PHP file compiles")
def c_php_syntax(ctx):
    g = _need_app(ctx)
    if g:
        return g
    if not PHP:
        return skip("php not on PATH")
    files = ctx.app_php()
    if not files:
        return skip("no PHP files generated yet")
    failures = []
    for p in files:
        proc = subprocess.run([PHP, "-l", p], capture_output=True, text=True)
        if proc.returncode != 0:
            first = (proc.stdout + proc.stderr).strip().splitlines()
            failures.append(f"{ctx.rel(p)}: {first[0] if first else 'lint failed'}")
    return bad(f"{len(failures)}/{len(files)} file(s) fail php -l", failures) if failures else ok(
        f"{len(files)} files compile")


@check("app", "app.composer_pagination", "composer.json requires illuminate/pagination",
       gotcha="eloquent_pagination_needs_separate_package")
def c_composer_pagination(ctx):
    g = _need_app(ctx)
    if g:
        return g
    data = json.loads(ctx.read("composer.json"))
    req = data.get("require", {})
    if "illuminate/pagination" not in req:
        return bad("missing illuminate/pagination — bootstrap.php registers Paginator resolvers "
                   "on EVERY request, so this crashes at boot, not just on a list page")
    return ok(f"pinned at {req['illuminate/pagination']}")


@check("app", "app.no_larastan", "larastan is not required", gotcha="no_larastan_for_standalone_eloquent")
def c_no_larastan(ctx):
    g = _need_app(ctx)
    if g:
        return g
    data = json.loads(ctx.read("composer.json"))
    allreq = dict(data.get("require", {}), **data.get("require-dev", {}))
    hits = [k for k in allreq if "larastan" in k]
    return bad("larastan present — hard-crashes without illuminate/foundation", hits) if hits else ok()


@check("app", "app.profile_password_route", "GET+POST /profile/password are routed",
       gotcha="(blueprint) prebuilt_core_features.3_profile_management")
def c_profile_password(ctx):
    g = _need_app(ctx)
    if g:
        return g
    routes = ctx.read("routes", "web.php")
    if routes is None:
        return bad("routes/web.php missing")
    src = strip_comments(routes)
    problems = []
    if not re.search(r"->get\(\s*['\"]/profile/password['\"]", src):
        problems.append("no GET /profile/password — first login always lands here (must_change_password=1)")
    if not re.search(r"->post\(\s*['\"]/profile/password['\"]", src):
        problems.append("no POST /profile/password — the password form has nowhere to submit")
    if not ctx.exists("resources", "views", "profile", "password.twig"):
        problems.append("resources/views/profile/password.twig missing")
    return bad("first-login flow is broken", problems) if problems else ok("routed + view present")


@check("app", "app.middleware_call_sites", "Middleware constructors match their `new X(...)` call sites",
       gotcha="middleware_constructor_call_site_mismatch")
def c_call_sites(ctx):
    g = _need_app(ctx)
    if g:
        return g
    routes = ctx.read("routes", "web.php") or ""
    routes += ctx.read("public", "index.php") or ""
    src = strip_comments(routes)
    problems = []
    checked = 0
    for cls in ("AuthMiddleware", "RbacMiddleware", "RateLimitMiddleware", "CsrfViewMiddleware"):
        f = ctx.path("app", "Middleware", cls + ".php")
        if not os.path.exists(f):
            continue
        body = strip_comments(read_text(f))
        m = re.search(r"function\s+__construct\s*\((.*?)\)\s*\{", body, re.S)
        if not m:
            continue
        params = m.group(1)
        # count top-level commas -> declared arity (0 params if blank)
        depth, arity = 0, (0 if not params.strip() else 1)
        for ch in params:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 0:
                arity += 1
        optional = len(re.findall(r"=\s*(?:null|\[\]|'|\"|\d)", params))
        for cm in re.finditer(r"new\s+" + cls + r"\s*\((.*?)\)\s*[,);]", src, re.S):
            checked += 1
            args = cm.group(1)
            d, n = 0, (0 if not args.strip() else 1)
            for ch in args:
                if ch in "([{":
                    d += 1
                elif ch in ")]}":
                    d -= 1
                elif ch == "," and d == 0:
                    n += 1
            if not (arity - optional <= n <= arity):
                problems.append(
                    f"new {cls}(...) passes {n} arg(s) but __construct declares {arity} "
                    f"({optional} optional) — this is the exact 7B crash signature")
    if not checked:
        return skip("no manual `new <Middleware>(...)` call sites found")
    return bad(f"{len(problems)} mismatch(es)", problems) if problems else ok(
        f"{checked} call site(s) match")


@check("app", "app.errorbag_all_not_firstofall", "Validation errors use ->all()[0], not ->firstOfAll()[0]",
       gotcha="rakit_errorbag_firstOfAll_is_keyed_by_field_not_sequential")
def c_errorbag(ctx):
    g = _need_app(ctx)
    if g:
        return g
    hits = grep(ctx.app_php(), r"firstOfAll\(\)\s*\[\s*0\s*\]")
    items = [f"{ctx.rel(p)}:{i}  {l}" for p, i, l in hits]
    return bad("firstOfAll() is keyed by field name; [0] is null -> TypeError on any real "
               "validation failure. Use ->all()[0].", items) if items else ok()


@check("app", "app.no_rakit_string_rule", "No 'string' rule passed to Rakit\\Validation",
       gotcha="rakit_validation_has_no_string_rule")
def c_rakit_string(ctx):
    g = _need_app(ctx)
    if g:
        return g
    hits = []
    for p in ctx.app_php():
        for i, line in enumerate(read_text(p).splitlines(), 1):
            for lit in re.findall(r"'([^']*\|[^']*)'|\"([^\"]*\|[^\"]*)\"", line):
                rule = lit[0] or lit[1]
                if "string" in [r.split(":")[0].strip() for r in rule.split("|")]:
                    hits.append(f"{ctx.rel(p)}:{i}  {rule}")
    return bad("Rakit ships no 'string' rule -> RuleNotFoundException at runtime", hits) if hits else ok()


@check("app", "app.twig_middleware_create", "TwigMiddleware::create(...) with explicit 'view' attribute",
       gotcha="twig_middleware_wiring")
def c_twig_mw(ctx):
    g = _need_app(ctx)
    if g:
        return g
    idx = ctx.read("public", "index.php")
    if idx is None:
        return bad("public/index.php missing")
    src = strip_comments(idx)
    if "TwigMiddleware::createFromContainer" in src:
        return bad("createFromContainer() never sets the 'view' request attribute -> "
                   "Twig::fromRequest() always throws. Use TwigMiddleware::create($app, $twig, 'view').")
    if "TwigMiddleware::create" not in src:
        return bad("no TwigMiddleware::create(...) in public/index.php")
    if not re.search(r"TwigMiddleware::create\s*\([^)]*['\"]view['\"]", src, re.S):
        return bad("TwigMiddleware::create(...) called without the third 'view' argument")
    return ok()


@check("app", "app.middleware_order", "index.php add() order puts TwigMiddleware after Guard",
       gotcha="middleware_add_order_includes_twig")
def c_mw_order(ctx):
    g = _need_app(ctx)
    if g:
        return g
    idx = ctx.read("public", "index.php")
    if idx is None:
        return bad("public/index.php missing")
    src = strip_comments(idx)
    pos = {}
    for name, pat in (("CsrfView", r"CsrfViewMiddleware"), ("Guard", r"Csrf\\?\\Guard|Guard::class|\$guard"),
                      ("Twig", r"TwigMiddleware::create"), ("Routing", r"addRoutingMiddleware"),
                      ("BodyParsing", r"addBodyParsingMiddleware"), ("Error", r"addErrorMiddleware")):
        m = re.search(pat, src)
        if m:
            pos[name] = m.start()
    need = ["CsrfView", "Guard", "Twig", "Routing", "BodyParsing", "Error"]
    have = [n for n in need if n in pos]
    if len(have) < 4:
        return skip(f"only found {have} in index.php; too little to order-check")
    seq = sorted(have, key=lambda n: pos[n])
    expect = [n for n in need if n in have]
    if seq != expect:
        return bad(f"add() order is {seq}, expected {expect} (Slim is FILO: Twig must EXECUTE "
                   f"before CsrfView, so it is add()ed after it)")
    return ok(" -> ".join(seq))


@check("app", "app.session_save", "session->save() is called after handler returns",
       gotcha="session_never_persisted_without_save")
def c_session_save(ctx):
    g = _need_app(ctx)
    if g:
        return g
    hits = grep(ctx.app_php(), r"->save\(\s*\)")
    if not hits:
        return bad("no ->save() anywhere — Odan keeps mutations in an in-memory snapshot; "
                   "login 302s but the next request has an empty session")
    return ok(f"{len(hits)} call site(s): " + ", ".join(f"{ctx.rel(p)}:{i}" for p, i, _ in hits[:3]))


@check("app", "app.session_get_arity", "SessionInterface::get() called with exactly one argument",
       gotcha="odan_session_get_has_no_default_param")
def c_session_get(ctx):
    g = _need_app(ctx)
    if g:
        return g
    hits = grep(ctx.app_php(), r"session\s*(?:->|\)->)\s*get\s*\([^()]*,", re.I)
    items = [f"{ctx.rel(p)}:{i}  {l}" for p, i, l in hits]
    return bad("Odan's get() takes ONE param; the 2nd is silently ignored and the default "
               "never applies. Use $session->get($k) ?? $default.", items) if items else ok()


@check("app", "app.csrf_storage", "Slim\\Csrf\\Guard uses session-backed storage",
       gotcha="csrf_storage_conflicts_with_session_save")
def c_csrf_storage(ctx):
    g = _need_app(ctx)
    if g:
        return g
    php = ctx.app_php()
    if not grep(php, r"Guard\s*\("):
        return skip("no Slim\\Csrf\\Guard instantiation found")
    if ctx.exists("app", "Support", "SessionCsrfStorage.php") or grep(php, r"SessionCsrfStorage"):
        return ok("SessionCsrfStorage in use")
    return bad("Guard is using default storage, which writes $_SESSION['csrf'] by reference. "
               "session->save() then overwrites it with a stale snapshot -> every POST fails CSRF. "
               "Pass a SessionInterface-backed ArrayAccess storage.")


@check("app", "app.pagination_resolvers", "bootstrap.php registers the three Paginator resolvers",
       gotcha="pagination_resolvers_never_registered")
def c_paginator_resolvers(ctx):
    g = _need_app(ctx)
    if g:
        return g
    boot = ctx.read("app", "bootstrap.php")
    if boot is None:
        return bad("app/bootstrap.php missing")
    src = strip_comments(boot)
    missing = [r for r in ("currentPageResolver", "currentPathResolver", "queryStringResolver")
               if r not in src]
    return bad("standalone illuminate/pagination defaults to page 1 and path '/' without these — "
               "pagination is permanently stuck on page 1 no matter how correct the Twig is",
               missing) if missing else ok("all three registered")


@check("app", "app.pagination_macro", "Pagination footer is real Twig, not static markup",
       gotcha="pagination_footer_was_never_functional")
def c_pagination_macro(ctx):
    g = _need_app(ctx)
    if g:
        return g
    p = ctx.path("resources", "views", "partials", "_pagination.twig")
    if not os.path.exists(p):
        return bad("resources/views/partials/_pagination.twig missing")
    src = read_text(p)
    missing = [m for m in ("currentPage", "lastPage", "url(") if m not in src]
    if missing:
        return bad("macro does not call the real paginator API", missing)
    dead = [f"line {i}: {l}" for _, i, l in grep([p], r'href\s*=\s*"#"')]
    return bad("dead href=\"#\" links — this is exactly the 'illustrative markup' bug", dead) if dead else ok()


@check("app", "app.pagination_appends", "Controllers call ->appends() so filters survive paging",
       gotcha="pagination_footer_was_never_functional")
def c_pagination_appends(ctx):
    g = _need_app(ctx)
    if g:
        return g
    paginate = grep(ctx.walk("app/Controllers", ".php") + ctx.walk("app/Services", ".php"),
                    r"->paginate\s*\(")
    if not paginate:
        return skip("no ->paginate() calls yet")
    files = {p for p, _, _ in paginate}
    missing = [ctx.rel(p) for p in files if "appends(" not in read_text(p)]
    return bad("page links silently drop the active search filter", missing) if missing else ok(
        f"{len(files)} file(s) paginate, all call appends()")


@check("app", "app.sidebar_responsive", "Sidebar is a mobile drawer", gotcha="app_shell_not_responsive")
def c_sidebar_responsive(ctx):
    g = _need_app(ctx)
    if g:
        return g
    src = ctx.read("resources", "views", "partials", "sidebar.twig")
    if src is None:
        return bad("resources/views/partials/sidebar.twig missing")
    problems = [tok for tok in ('id="sidebar"', "-translate-x-full", "lg:translate-x-0", "lg:static")
                if tok not in src]
    return bad("sidebar has no mobile-drawer markup", problems) if problems else ok()


@check("app", "app.sidebar_not_inset_y", "Mobile sidebar uses top-16, never inset-y-0",
       gotcha="navbar_covered_by_mobile_sidebar")
def c_sidebar_inset(ctx):
    g = _need_app(ctx)
    if g:
        return g
    src = ctx.read("resources", "views", "partials", "sidebar.twig")
    if src is None:
        return bad("resources/views/partials/sidebar.twig missing")
    if "inset-y-0" in src:
        return bad("inset-y-0 on a fixed z-30 sidebar covers the non-fixed z-10 navbar — "
                   "the reported 'navbar disappeared' bug. Use top-16 lg:top-auto bottom-0 lg:bottom-auto.")
    if "top-16" not in src:
        return bad("no top-16 — mobile drawer must start exactly at the navbar's bottom edge (h-16)")
    return ok()


@check("app", "app.shell_ids_wired", "#sidebar-toggle and #sidebar-backdrop exist",
       gotcha="app_shell_not_responsive")
def c_shell_ids(ctx):
    g = _need_app(ctx)
    if g:
        return g
    problems = []
    nav = ctx.read("resources", "views", "partials", "navbar.twig")
    base = ctx.read("resources", "views", "layouts", "base.twig")
    if nav is None:
        problems.append("navbar.twig missing")
    elif 'id="sidebar-toggle"' not in nav:
        problems.append('navbar.twig has no id="sidebar-toggle" — the drawer can never be opened on mobile')
    if base is None:
        problems.append("base.twig missing")
    elif 'id="sidebar-backdrop"' not in base:
        problems.append('base.twig has no id="sidebar-backdrop" — no tap-outside-to-close overlay')
    return bad("app shell ids do not match app.js", problems) if problems else ok()


@check("app", "app.action_buttons_gated", "List-view action buttons are wrapped in can()",
       gotcha="action_buttons_not_permission_gated")
def c_buttons_gated(ctx):
    g = _need_app(ctx)
    if g:
        return g
    lists = [p for p in ctx.views() if os.path.basename(p) in ("index.twig", "list.twig")
             and "/views/dashboard/" not in ctx.rel(p) and "/views/profile/" not in ctx.rel(p)]
    if not lists:
        return skip("no CRUD list views generated yet")
    problems = []
    for p in lists:
        src = read_text(p)
        # action controls: links/buttons pointing at create/edit or a delete form
        has_actions = re.search(r"/(create|add|edit)\b|data-delete|method=\"post\".*delete", src, re.I | re.S)
        if has_actions and "can(" not in src:
            problems.append(f"{ctx.rel(p)}: renders action controls with no {{% if can(...) %}} gate")
    return bad("route-level RBAC blocks the request, but the button is still shown — both layers "
               "are required", problems) if problems else ok(f"{len(lists)} list view(s) gated")


@check("app", "app.request_action_filter", "{Model}Request::validate() filters rules by action",
       gotcha="field_schema_rules_must_be_filtered_by_action")
def c_request_action(ctx):
    g = _need_app(ctx)
    if g:
        return g
    reqs = ctx.walk("app/Requests", ".php")
    schema_driven = [p for p in reqs if "FieldSchema" in read_text(p) or "field_schema" in read_text(p)]
    if not schema_driven:
        return skip("no field-schema-driven Request classes yet")
    problems = []
    for p in schema_driven:
        src = strip_comments(read_text(p))
        m = re.search(r"function\s+validate\s*\(([^)]*)\)", src)
        if not m or "$action" not in m.group(1):
            problems.append(f"{ctx.rel(p)}: validate() takes no $action parameter")
        elif "show_in" not in src:
            problems.append(f"{ctx.rel(p)}: never filters on show_in")
    return bad("edit will fail on add-only fields (e.g. password required on Edit)",
               problems) if problems else ok(f"{len(schema_driven)} Request class(es) action-aware")


@check("app", "app.hooks_present", "Every Service has a companion Hooks class", gotcha="(hook_protocol)")
def c_hooks(ctx):
    g = _need_app(ctx)
    if g:
        return g
    services = ctx.walk("app/Services", ".php")
    models = [os.path.basename(p)[:-len("Service.php")] for p in services
              if p.endswith("Service.php") and os.path.basename(p) not in ("AuthService.php", "AuditService.php", "ProfileService.php")]
    if not models:
        return skip("no module services generated yet")
    missing = [f"app/Hooks/{m}Hooks.php" for m in models if not ctx.exists("app", "Hooks", m + "Hooks.php")]
    return bad("regenerating the Service will destroy business logic with nowhere else to live",
               missing) if missing else ok(f"{len(models)} module(s) have hooks")


@check("app", "app.no_laravel_facades", "No Laravel facades / Illuminate HTTP in generated code",
       gotcha="(identity.rules STRICT_FRAMEWORK_RULE)")
def c_no_facades(ctx):
    g = _need_app(ctx)
    if g:
        return g
    hits = grep(ctx.app_php(),
                r"Illuminate\\Http\\Request|Illuminate\\Foundation|\bDB::|\bView::|\bValidator::|\bRoute::|FormRequest")
    items = [f"{ctx.rel(p)}:{i}  {l}" for p, i, l in hits]
    return bad("this is Slim 4, not Laravel — none of these exist at runtime", items) if items else ok()


@check("app", "app.no_cdn", "Views reference no external CDN", gotcha="(identity.rules NO_EXTERNAL_FETCH)")
def c_no_cdn(ctx):
    g = _need_app(ctx)
    if g:
        return g
    views = ctx.views()
    if not views:
        return skip("no views generated yet")
    hits = grep(views, r'(?:src|href)\s*=\s*["\']https?://')
    items = [f"{ctx.rel(p)}:{i}  {l[:120]}" for p, i, l in hits]
    return bad("assets must come from /assets/vendor/, which is already provisioned", items) if items else ok(
        f"{len(views)} views clean")


@check("app", "app.no_dark_classes", "No dark: variants (design_system.dark_mode is off)",
       gotcha="(design_system.dark_mode)")
def c_no_dark(ctx):
    g = _need_app(ctx)
    if g:
        return g
    views = ctx.views()
    if not views:
        return skip("no views generated yet")
    hits = grep(views, r"\bdark:[a-z]")
    items = [f"{ctx.rel(p)}:{i}" for p, i, _ in hits]
    return bad(f"{len(items)} line(s) carry dark: classes copied from the Flowbite reference",
               items[:20]) if items else ok(f"{len(views)} views clean")


@check("app", "app.brain_updated", "PROJECT_BRAIN.json reflects the generated app",
       gotcha="(project_brain_protocol)")
def c_brain_updated(ctx):
    g = _need_app(ctx)
    if g:
        return g
    raw = ctx.read("PROJECT_BRAIN.json")
    if raw is None:
        return bad("PROJECT_BRAIN.json missing on a project that has code")
    brain = json.loads(raw)
    if not brain.get("modules_completed"):
        return bad("app/ has code but modules_completed is empty — the brain was never evolved")
    return ok(f"{len(brain['modules_completed'])} module(s) recorded")


# ===========================================================================
# TIER: runtime — needs composer install and (for HTTP checks) a database.
# ===========================================================================

@check("runtime", "runtime.composer_validate", "composer.json validates")
def c_composer_validate(ctx):
    g = _need_app(ctx)
    if g:
        return g
    if not COMPOSER:
        return skip("composer not on PATH")
    proc = subprocess.run([COMPOSER, "validate", "--no-check-publish", "--no-interaction"],
                          cwd=ctx.target, capture_output=True, text=True)
    if proc.returncode != 0:
        return bad("composer validate failed", (proc.stdout + proc.stderr).strip().splitlines()[:10])
    return ok()


@check("runtime", "runtime.vendor_installed", "Dependencies are installed")
def c_vendor(ctx):
    g = _need_app(ctx)
    if g:
        return g
    if not os.path.isdir(ctx.path("vendor")):
        return skip("vendor/ not present — run `composer install` to enable runtime checks")
    return ok()


@check("runtime", "runtime.boot", "public/index.php boots without a fatal error")
def c_boot(ctx):
    g = _need_app(ctx)
    if g:
        return g
    if not PHP:
        return skip("php not on PATH")
    if not os.path.isdir(ctx.path("vendor")):
        return skip("vendor/ not present — run `composer install` first")
    if not ctx.exists(".env"):
        return skip(".env not present — boot needs DB config")
    proc = subprocess.run([PHP, "-r", "$_SERVER['REQUEST_URI']='/login';$_SERVER['REQUEST_METHOD']='GET';"
                                      "ob_start(); require 'public/index.php'; ob_end_clean();"],
                          cwd=ctx.target, capture_output=True, text=True, timeout=60)
    err = (proc.stdout + proc.stderr).strip()
    if re.search(r"Fatal error|Uncaught|Parse error", err):
        return bad("fatal on boot", err.splitlines()[:8])
    return ok("no fatal")


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

TIER_ORDER = ["spec", "app", "runtime"]
TIER_BLURB = {
    "spec": "validates this spec repo itself",
    "app": "static regression checks on the generated app",
    "runtime": "needs composer install / database",
}


def coverage_report(ctx):
    gotchas = [k for k in ctx.spec.get("verified_gotchas", {}) if k != "description"]
    guarded = {}
    for fn in CHECKS:
        if fn.gotcha and not fn.gotcha.startswith("("):
            guarded.setdefault(fn.gotcha, []).append(fn.cid)
    print("verified_gotchas coverage\n" + "=" * 62)
    unguarded = []
    for k in gotchas:
        if k in guarded:
            print(f"  [x] {k}\n        guarded by: {', '.join(guarded[k])}")
        else:
            unguarded.append(k)
            print(f"  [ ] {k}")
    print("-" * 62)
    print(f"  {len(gotchas) - len(unguarded)}/{len(gotchas)} gotchas guarded by at least one check")
    extra = [g for g in guarded if g not in gotchas]
    if extra:
        print(f"  WARNING: checks reference unknown gotcha keys: {extra}")
    return 0 if not extra else 1


def main():
    ap = argparse.ArgumentParser(description="wVictory eval harness")
    ap.add_argument("--target", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--tier", default="all", choices=["all"] + TIER_ORDER)
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true", help="show detail for PASS too")
    args = ap.parse_args()

    ctx = Ctx(args.target)
    if args.coverage:
        sys.exit(coverage_report(ctx))

    selected = TIER_ORDER if args.tier == "all" else [args.tier]
    results = []
    for fn in CHECKS:
        if fn.tier not in selected:
            continue
        try:
            res = fn(ctx)
        except Exception as exc:
            res = Result(FAIL, f"check itself raised: {type(exc).__name__}: {exc}")
        results.append((fn, res))

    if args.as_json:
        print(json.dumps([{
            "id": fn.cid, "tier": fn.tier, "desc": fn.desc, "gotcha": fn.gotcha,
            "status": r.status, "detail": r.detail, "items": r.items,
        } for fn, r in results], indent=2))
    else:
        print(f"wVictory eval — target: {ctx.target}\n")
        for tier in selected:
            rows = [(f, r) for f, r in results if f.tier == tier]
            if not rows:
                continue
            print(f"[{tier}] {TIER_BLURB[tier]}")
            for fn, r in rows:
                print(f"  {r.status:4}  {fn.cid:34} {fn.desc}")
                if r.detail and (r.status != PASS or args.verbose):
                    print(f"          -> {r.detail}")
                for it in r.items[:12]:
                    print(f"           - {it}")
                if len(r.items) > 12:
                    print(f"           - ... and {len(r.items) - 12} more")
            print()
        counts = {s: sum(1 for _, r in results if r.status == s) for s in (PASS, FAIL, SKIP)}
        print("=" * 62)
        print(f"  {counts[PASS]} passed   {counts[FAIL]} failed   {counts[SKIP]} skipped")
        if counts[FAIL]:
            print("\n  A FAIL means the generated app has a bug this spec already knows about.")
            print("  Fix the CANONICAL SNIPPET, not just the generated file.")

    sys.exit(1 if any(r.status == FAIL for _, r in results) else 0)


if __name__ == "__main__":
    main()
