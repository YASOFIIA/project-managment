"""Architecture enforcement tests.

Guarantees clean layer separation:
- Services/Application and Domain layers must never import HTTPException or fastapi.status.
- Domain layer must never import web frameworks (FastAPI/Starlette), ORM (SQLAlchemy),
  or configuration (pydantic-settings).
"""

from __future__ import annotations

import ast
from pathlib import Path


def _get_forbidden_imports_in_dir(directory: Path) -> list[str]:
    """Inspect Python AST in directory and return violations of layer decoupling rules."""
    violations: list[str] = []
    if not directory.exists():
        return violations

    for py_file in directory.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            # 1. from <module> import <name>
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    # Forbid importing HTTPException
                    if alias.name == "HTTPException":
                        violations.append(
                            f"{py_file.name}:{node.lineno} imports HTTPException from '{module}'"
                        )
                    # Forbid importing status from fastapi/starlette
                    if alias.name == "status" and ("fastapi" in module or "starlette" in module):
                        violations.append(
                            f"{py_file.name}:{node.lineno} imports status from '{module}'"
                        )

            # 2. import <module>
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "status" in alias.name and (
                        "fastapi" in alias.name or "starlette" in alias.name
                    ):
                        violations.append(f"{py_file.name}:{node.lineno} imports '{alias.name}'")

    return violations


def test_services_and_domain_layers_do_not_import_http_exceptions_or_status() -> None:
    """Verify services, application, and domain layers do not depend on HTTP exceptions."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    src_app = repo_root / "src" / "app"

    checked_dirs = [
        src_app / "services",
        src_app / "application",
        src_app / "domain",
    ]

    all_violations: list[str] = []
    for directory in checked_dirs:
        violations = _get_forbidden_imports_in_dir(directory)
        all_violations.extend(violations)

    msg = (
        "Clean architecture violation: services/domain layers must not import HTTPException:\n"
        + "\n".join(all_violations)
    )
    assert not all_violations, msg


def test_domain_layer_does_not_import_frameworks_or_orm() -> None:
    """Verify domain layer has zero dependencies on web frameworks, ORM, or config loaders."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    domain_dir = repo_root / "src" / "app" / "domain"
    if not domain_dir.exists():
        return

    forbidden_prefixes = ("fastapi", "starlette", "sqlalchemy", "pydantic_settings")
    violations: list[str] = []

    for py_file in domain_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if any(module.startswith(prefix) for prefix in forbidden_prefixes):
                    violations.append(
                        f"{py_file.name}:{node.lineno} imports from forbidden '{module}'"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(prefix) for prefix in forbidden_prefixes):
                        violations.append(
                            f"{py_file.name}:{node.lineno} imports forbidden '{alias.name}'"
                        )

    msg = "Domain layer violation: domain must not import frameworks or ORM:\n" + "\n".join(
        violations
    )
    assert not violations, msg


def test_services_do_not_import_sqlalchemy_except_temporary_documents() -> None:
    """Verify services layer (auth, projects, access) does not import sqlalchemy."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    services_dir = repo_root / "src" / "app" / "services"
    if not services_dir.exists():
        return

    # Temporary exemption list to be removed in step R3.3
    temporary_exceptions = {"documents.py"}
    forbidden_prefixes = ("sqlalchemy",)
    violations: list[str] = []

    for py_file in services_dir.glob("*.py"):
        if py_file.name in temporary_exceptions:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if any(module.startswith(p) for p in forbidden_prefixes):
                    violations.append(
                        f"{py_file.name}:{node.lineno} imports from forbidden '{module}'"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(p) for p in forbidden_prefixes):
                        violations.append(
                            f"{py_file.name}:{node.lineno} imports forbidden '{alias.name}'"
                        )

    msg = (
        "Clean architecture violation: services must not import sqlalchemy "
        "(exempted: documents.py until R3.3):\n" + "\n".join(violations)
    )
    assert not violations, msg
