#!/usr/bin/env python3
"""
Lightweight architecture boundary checks for Spark API package.

This script enforces a few high-signal import rules to prevent layer drift.
It is intentionally simple and conservative (AST-based import scanning).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SPARK_ROOT = REPO_ROOT / "apps" / "api" / "src" / "spark"
GRAPH_REPOSITORIES_ROOT = SPARK_ROOT / "graph" / "repositories"


@dataclass(frozen=True)
class Rule:
    source_prefix: str
    forbidden_prefixes: tuple[str, ...]
    description: str


RULES: tuple[Rule, ...] = (
    Rule(
        source_prefix="spark.models.",
        forbidden_prefixes=("spark.routers.", "spark.services.", "spark.agents."),
        description="models must stay framework/business-orchestration free",
    ),
    Rule(
        source_prefix="spark.services.",
        forbidden_prefixes=("spark.routers.",),
        description="services must not depend on HTTP transport layer",
    ),
    Rule(
        source_prefix="spark.db.",
        forbidden_prefixes=("spark.routers.", "spark.services.", "spark.agents."),
        description="db layer must remain low-level and transport-agnostic",
    ),
    Rule(
        source_prefix="spark.repositories.",
        forbidden_prefixes=("spark.routers.", "spark.agents."),
        description="repositories must not depend on transport or agent adapters",
    ),
)


def module_name_from_path(path: Path) -> str:
    rel = path.relative_to(SPARK_ROOT).with_suffix("")
    parts = ".".join(rel.parts)
    return f"spark.{parts}"


def iter_imports(tree: ast.AST, current_module: str) -> list[str]:
    imports: list[str] = []
    current_parts = current_module.split(".")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                if node.level == 0:
                    imports.append(node.module)
                else:
                    base_parts = current_parts[: -node.level]
                    imports.append(".".join(base_parts + node.module.split(".")))
            elif node.level > 0:
                imports.append(".".join(current_parts[: -node.level]))
    return imports


def is_forbidden(source_module: str, imported_module: str) -> tuple[bool, str]:
    for rule in RULES:
        if source_module == rule.source_prefix[:-1] or source_module.startswith(
            rule.source_prefix
        ):
            for forbidden in rule.forbidden_prefixes:
                if imported_module == forbidden[:-1] or imported_module.startswith(
                    forbidden
                ):
                    return True, rule.description
    return False, ""


def graph_query_imports(tree: ast.AST) -> set[str]:
    """Return imported graph query modules for a repository file."""
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("spark.graph.queries"):
                    imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if not node.module:
                continue
            if node.module == "spark.graph.queries":
                for alias in node.names:
                    imports.add(f"spark.graph.queries.{alias.name}")
            elif node.module.startswith("spark.graph.queries."):
                imports.add(node.module)
    return imports


def expected_graph_query_module_for(repo_file: Path) -> str | None:
    stem = repo_file.stem
    if stem in {"__init__", "repository"}:
        return None
    return f"spark.graph.queries.{stem}"


def main() -> int:
    violations: list[str] = []
    for py_file in sorted(SPARK_ROOT.rglob("*.py")):
        module = module_name_from_path(py_file)
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception as exc:  # pragma: no cover - surfaced as CI failure text
            violations.append(f"{py_file}: unable to parse ({exc})")
            continue

        for imported in iter_imports(tree, module):
            forbidden, reason = is_forbidden(module, imported)
            if forbidden:
                rel = py_file.relative_to(REPO_ROOT)
                violations.append(f"{rel}: {module} imports {imported} ({reason})")

        expected_query_module = expected_graph_query_module_for(py_file)
        if (
            expected_query_module is not None
            and py_file.parent == GRAPH_REPOSITORIES_ROOT
        ):
            imported_graph_queries = graph_query_imports(tree)
            if expected_query_module not in imported_graph_queries:
                rel = py_file.relative_to(REPO_ROOT)
                violations.append(
                    f"{rel}: must import its matching query module "
                    f"({expected_query_module})"
                )

    if violations:
        print("Architecture boundary check failed:\n")
        for item in violations:
            print(f"- {item}")
        print(
            "\nIf this dependency is intentional, update docs/architecture/ARCHITECTURE-GUARDRAILS.md "
            "and this script in the same change."
        )
        return 1

    print("Architecture boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
