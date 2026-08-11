#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spec.py — read mini_framework.json in small pieces instead of all 86 KB at once.

The spec is ~22k tokens. Loading it whole on every task is what makes a small
model lose the part that actually mattered. Every command below prints one
focused slice.

    python tools/spec.py map                 # pipeline steps -> which snippet each needs
    python tools/spec.py rules               # the non-negotiable rules, nothing else
    python tools/spec.py step 6              # one pipeline step in full
    python tools/spec.py list                # every canonical snippet key + target path
    python tools/spec.py show <key>          # one snippet: target_path, note, literal code
    python tools/spec.py gotcha              # list the verified gotchas
    python tools/spec.py gotcha <key>        # one gotcha in full
    python tools/spec.py grep <text>         # find which slice mentions <text>

<key> is a dotted path under canonical_snippets, e.g.
    starter_middleware_pattern.rbac_middleware_template
Prefixes are fine as long as they are unambiguous: `show pagination` works.
"""

from __future__ import annotations

import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "mini_framework.json")

# Which canonical_snippets / rules each pipeline step actually needs. This is the
# routing table the whole point of this script rests on: step 6 does not need the
# 9 KB RBAC forms pattern, so it should never have to read it.
STEP_HINTS = {
    1: [],
    2: [],  # the requirement text is self-sufficient; no snippet needed
    3: ["eloquent_capsule_bootstrap"],
    4: ["field_schema_pattern.field_schema_template",
        "field_schema_pattern.request_deriving_rules_from_schema"],
    5: ["hooks_pattern.hooks_class_template", "hooks_pattern.service_calling_hooks_example"],
    6: ["twig_custom_extensions"],
    7: ["controller_twig_render", "pagination_pattern.controller_must_call_appends"],
    # All four MUST be read together — CONSTRUCTOR_CALL_SITE_PAIRING: the class and
    # its `new X(...)` line come from the same entry, in the same step, or they drift.
    8: ["starter_middleware_pattern.auth_middleware_template",
        "starter_middleware_pattern.rbac_middleware_template",
        "starter_middleware_pattern.rate_limit_middleware_template",
        "starter_middleware_pattern.route_wiring_matching_call_sites"],
    9: ["field_schema_pattern.form_field_macro_template",
        "field_schema_pattern.add_edit_view_usage",
        "field_schema_pattern.list_columns_usage",
        "pagination_pattern.fixed_footer_macro_template"],
    10: ["menu_registry_pattern.menu_php_template"],
}


def load():
    with io.open(SPEC, encoding="utf-8") as fh:
        return json.load(fh)


def flatten(node, prefix=""):
    """dotted_key -> dict, for every canonical_snippets entry that has code."""
    out = {}
    if isinstance(node, dict):
        if isinstance(node.get("code"), str):
            out[prefix] = node
        for k, v in node.items():
            if isinstance(v, dict):
                out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
    return out


def resolve(entries, key):
    if key in entries:
        return key
    hits = [k for k in entries if k.startswith(key)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        hits = [k for k in entries if key.lower() in k.lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"no snippet matches '{key}'. Try: python tools/spec.py list")
    sys.exit("ambiguous, pick one:\n  " + "\n  ".join(hits))


def wrap(text, width=96, indent="    "):
    out, line = [], ""
    for word in str(text).split():
        if len(line) + len(word) + 1 > width:
            out.append(indent + line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(indent + line)
    return "\n".join(out)


def cmd_map(d):
    entries = flatten(d.get("canonical_snippets", {}))
    print("10-STEP PIPELINE — run in order. Skipping a step is the #1 cause of a")
    print("module nobody can reach (usually the permission seeder or the menu entry).\n")
    for s in d["execution_pipeline"]["steps"]:
        n = s["step"]
        print(f"  {n:2}. {s['name']}")
        if s.get("target_path_pattern"):
            print(f"      -> {s['target_path_pattern']}")
        for h in STEP_HINTS.get(n, []):
            size = len(entries[h]["code"]) if h in entries else "?"
            print(f"      read: canonical_snippets.{h}  ({size} chars)")
    print("\nAfter the last step: update PROJECT_BRAIN.json, then run")
    print("  python eval/run.py --tier app")


def cmd_rules(d):
    print("IDENTITY RULES (mini_framework.json -> identity.rules)\n")
    for r in d["identity"]["rules"]:
        name, _, body = r.partition(":")
        print(f"  * {name.strip()}")
        print(wrap(body.strip() or name, indent="      "))
        print()
    print("TECH STACK")
    tb = d["tech_stack"]["backend"]
    print(f"  {tb['language']} | {tb['framework'].split('.')[0]} | {tb['di_container']} | {tb['orm']}")
    print(f"  Views: Twig | CSS: {d['tech_stack']['frontend']['css_framework']}")
    print(f"  Dark mode: {'ON' if 'NOT' not in d['design_system']['dark_mode'][:20] else 'OFF'}")
    print("\nDESIGN TOKENS (use these exact values, do not invent near-identical ones)")
    for k, v in d["design_system"]["tokens"].items():
        print(f"  {k:16} {v}")


def cmd_step(d, n):
    n = int(n)
    steps = {s["step"]: s for s in d["execution_pipeline"]["steps"]}
    if n not in steps:
        sys.exit(f"step must be 1..{max(steps)}")
    s = steps[n]
    print(f"STEP {n}: {s['name']}")
    if s.get("target_path_pattern"):
        print(f"target: {s['target_path_pattern']}")
    if s.get("owasp_ref"):
        print(f"owasp:  {s['owasp_ref']}")
    print()
    for r in s.get("requirements", []):
        name, _, body = str(r).partition(":")
        if body.strip():
            print(f"  * {name.strip()}")
            print(wrap(body.strip(), indent="      "))
        else:
            print(f"  * {name.strip()}")
        print()
    if s.get("template"):
        print("TEMPLATE\n" + s["template"])
    if s.get("template_instructions"):
        print("INSTRUCTIONS\n" + wrap(s["template_instructions"], indent="  "))
    hints = STEP_HINTS.get(n, [])
    if hints:
        print("COPY VERBATIM FROM (do not write these from memory):")
        for h in hints:
            print(f"  python tools/spec.py show {h}")


def cmd_list(d):
    entries = flatten(d.get("canonical_snippets", {}))
    print(f"{len(entries)} canonical snippets — copy these VERBATIM, never from memory\n")
    for k in sorted(entries):
        e = entries[k]
        tp = (e.get("target_path") or "").split("—")[0].split(" - ")[0].strip()
        print(f"  {k}")
        print(f"      {len(e['code']):>5} chars  ->  {tp or '(fragment)'}")


def cmd_show(d, key):
    entries = flatten(d.get("canonical_snippets", {}))
    k = resolve(entries, key)
    e = entries[k]
    print(f"=== canonical_snippets.{k} ===")
    if e.get("target_path"):
        print(f"\nTARGET PATH\n{wrap(e['target_path'], indent='  ')}")
    for extra in ("creation_rule", "note", "VERSION_PINS_ARE_EXACT_DO_NOT_LOOSEN"):
        if e.get(extra):
            print(f"\n{extra.upper()}\n{wrap(e[extra], indent='  ')}")
    print("\nCODE (copy verbatim)\n" + "-" * 70)
    print(e["code"])
    print("-" * 70)


def cmd_gotcha(d, key=None):
    g = {k: v for k, v in d["verified_gotchas"].items() if k != "description"}
    if key is None:
        print(f"{len(g)} verified gotchas — every one is a bug that ACTUALLY happened.\n")
        for k, v in g.items():
            first = str(v).split(". ")[0]
            print(f"  {k}")
            print(wrap(first[:180] + ("..." if len(first) > 180 else ""), indent="      "))
        print("\n  python tools/spec.py gotcha <key>     for the full entry")
        print("  python eval/run.py --coverage         which ones the test suite guards")
        return
    hits = [k for k in g if key.lower() in k.lower()]
    if not hits:
        sys.exit(f"no gotcha matches '{key}'")
    for k in hits:
        print(f"=== {k} ===\n{wrap(g[k], indent='  ')}\n")


def cmd_grep(d, needle):
    needle_l = needle.lower()
    found = 0

    def rec(node, path):
        nonlocal found
        if isinstance(node, dict):
            for k, v in node.items():
                rec(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                rec(v, f"{path}[{i}]")
        elif isinstance(node, str) and needle_l in node.lower():
            found += 1
            i = node.lower().index(needle_l)
            frag = node[max(0, i - 90):i + 110].replace("\n", " ")
            print(f"  {path}\n      ...{frag}...")

    print(f"'{needle}' in mini_framework.json:\n")
    rec(d, "")
    if not found:
        print("  (no match)")
    else:
        print(f"\n  {found} match(es)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    d = load()
    cmd, rest = sys.argv[1], sys.argv[2:]
    table = {
        "map": lambda: cmd_map(d),
        "rules": lambda: cmd_rules(d),
        "step": lambda: cmd_step(d, rest[0]),
        "list": lambda: cmd_list(d),
        "show": lambda: cmd_show(d, rest[0]),
        "gotcha": lambda: cmd_gotcha(d, rest[0] if rest else None),
        "grep": lambda: cmd_grep(d, " ".join(rest)),
    }
    if cmd not in table:
        sys.exit(f"unknown command '{cmd}'\n{__doc__}")
    if cmd in ("step", "show") and not rest:
        sys.exit(f"'{cmd}' needs an argument")
    table[cmd]()


if __name__ == "__main__":
    main()
