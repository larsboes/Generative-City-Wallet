#!/usr/bin/env python3
"""
Guardrails for HTTP routers.

Routers should stay transport adapters and must not create database connections
directly. Persistence lifecycle belongs in services/repositories.
"""

from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTERS_ROOT = REPO_ROOT / "apps" / "api" / "src" / "spark" / "routers"
ALLOWED_ROUTER_REPOSITORY_IMPORTS: set[str] = {
    "apps/api/src/spark/routers/graph.py",
}


def has_forbidden_router_db_usage(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "spark.db.connection":
                for alias in node.names:
                    if alias.name == "get_connection":
                        return True
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "get_connection":
                return True
    return False


def has_forbidden_router_repository_import(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("spark.repositories."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("spark.repositories."):
                return True
    return False


def main() -> int:
    violations: list[str] = []
    for py_file in sorted(ROUTERS_ROOT.rglob("*.py")):
        rel = py_file.relative_to(REPO_ROOT).as_posix()
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            violations.append(f"{rel}: unable to parse ({exc})")
            continue

        if has_forbidden_router_db_usage(tree):
            violations.append(
                f"{rel}: routers must not call/get `get_connection`; route via services"
            )
        if (
            rel not in ALLOWED_ROUTER_REPOSITORY_IMPORTS
            and has_forbidden_router_repository_import(tree)
        ):
            violations.append(
                f"{rel}: routers must not import repositories directly; route via services"
            )

    if violations:
        print("Router boundary check failed:\n")
        for item in violations:
            print(f"- {item}")
        return 1

    print("Router boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
