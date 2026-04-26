#!/usr/bin/env python3
"""
Guard against new direct SQL usage inside spark.services.

Architecture target: services orchestrate policy and call repositories for persistence.
To roll this out safely, we keep a baseline allowlist for legacy files that still contain
direct SQL calls. New service modules must stay SQL-free.
"""

from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICES_ROOT = REPO_ROOT / "apps" / "api" / "src" / "spark" / "services"

# Legacy exceptions until refactored to repositories.
ALLOWED_LEGACY_SERVICE_FILES: set[str] = set()


def has_direct_sql_usage(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Detect common direct SQL execution pattern: <expr>.execute(...)
            if isinstance(node.func, ast.Attribute) and node.func.attr == "execute":
                return True
    return False


def main() -> int:
    violations: list[str] = []

    for py_file in sorted(SERVICES_ROOT.rglob("*.py")):
        rel = py_file.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWED_LEGACY_SERVICE_FILES:
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            violations.append(f"{rel}: unable to parse ({exc})")
            continue

        if has_direct_sql_usage(tree):
            violations.append(
                f"{rel}: direct SQL call detected in services layer; route persistence through spark.repositories"
            )

    if violations:
        print("Service SQL boundary check failed:\n")
        for item in violations:
            print(f"- {item}")
        print(
            "\nIf this is an intentional temporary exception, add the file to "
            "ALLOWED_LEGACY_SERVICE_FILES with a refactor note in docs/architecture/CODE-MAP.md."
        )
        return 1

    print("Service SQL boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
