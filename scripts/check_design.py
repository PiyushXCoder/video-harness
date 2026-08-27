#!/usr/bin/env python3
"""
check_design.py -- fail the build when a component hardcodes a design value.

DESIGN.md is prose and cannot be parsed reliably; it is read by an agent, not a
script. But CODE is structured, so the rule that DESIGN.md's values live in
exactly one place per engine CAN be enforced mechanically -- which is where the
repo's "encode editorial rules as build-time failures" philosophy actually
applies here.

Two design modules are allowed to name raw values:
    .remotion/src/design.ts      (Remotion)
    .manim/scenes/design.py      (Manim)
Everything else must import a token. A composition that writes `#1ed760` or
`fontSize: 52` has forked the design system, and the fork is invisible until
someone swaps DESIGN.md and half the video fails to change.

Usage:
  check_design.py            # report and exit non-zero on any violation
  check_design.py --list     # report only, exit 0 (for a work list)
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The two hand-authored translations of DESIGN.md. Raw values belong here.
DESIGN_MODULES = {
    REPO_ROOT / ".remotion" / "src" / "design.ts",
    REPO_ROOT / ".manim" / "scenes" / "design.py",
}

SCAN = [
    (REPO_ROOT / ".remotion" / "src", ("*.tsx", "*.ts")),
    (REPO_ROOT / ".manim" / "scenes", ("*.py",)),
]

SKIP_DIRS = {"node_modules", "media", "__pycache__"}

RULES = [
    # (name, pattern, hint)
    ("raw hex colour", re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b"),
     "use a ROLE.* token (or PALETTE.* if you truly need the raw name)"),
    ("literal fontSize", re.compile(r"fontSize:\s*\d+"),
     "use TYPE.<role>.size"),
    ("literal fontWeight", re.compile(r"fontWeight:\s*\d+"),
     "use TYPE.<role>.weight"),
    ("literal rgb/rgba", re.compile(r"\brgba?\(\s*\d"),
     "use a SHADOW.* recipe or a ROLE.* colour"),
    ("literal font_size (manim)", re.compile(r"font_size\s*=\s*\d+"),
     "use a TYPE size from design.py"),
]

# Lines that are comments or docstrings are documentation, not code -- a comment
# explaining WHY a value is 232 is exactly what we want to keep.
COMMENT = re.compile(r"^\s*(//|/\*|\*|#)")


def iter_files():
    for root, globs in SCAN:
        if not root.is_dir():
            continue
        for pattern in globs:
            for p in sorted(root.rglob(pattern)):
                if any(part in SKIP_DIRS for part in p.parts):
                    continue
                if p.resolve() in DESIGN_MODULES:
                    continue
                yield p


def main():
    list_only = "--list" in sys.argv
    violations = []

    for path in iter_files():
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if COMMENT.match(line):
                continue
            for name, pattern, hint in RULES:
                m = pattern.search(line)
                if m:
                    violations.append((path, n, name, m.group(0), hint, line.strip()))

    if not violations:
        print("check_design: clean — every design value comes from a design module.")
        return 0

    by_file = {}
    for v in violations:
        by_file.setdefault(v[0], []).append(v)

    for path, items in by_file.items():
        print(f"\n{path.relative_to(REPO_ROOT)}")
        for _, n, name, found, hint, line in items:
            print(f"  {n:4d}  {name}: {found}")
            print(f"        {line[:96]}")
            print(f"        -> {hint}")

    print(f"\n{len(violations)} violation(s) in {len(by_file)} file(s).")
    print("Design values live in .remotion/src/design.ts and .manim/scenes/design.py "
          "only — see DESIGN.md section 11.")
    return 0 if list_only else 1


if __name__ == "__main__":
    sys.exit(main())
