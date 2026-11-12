"""Architecture enforcement tests.

Guarantees clean layer separation according to Clean Architecture:
- Services/Application and Domain layers must never import HTTPException or status.
- Services and Application layers must never import sqlalchemy, starlette, boto3,
  app.infrastructure, or app.api. (fastapi only in documents.py for UploadFile until R4).
- Domain layer must never import web frameworks, ORM, config, services, api, or infrastructure.
- API layer must only import app.infrastructure in deps.py.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _collect_module_imports(py_file: Path) -> list[tuple[int, str, list[str]]]:
    """Return list of (lineno, module_name, [imported_names]) for each import in a Python file."""
    imports: list[tuple[int, str, list[str]]] = []
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            imports.append((node.lineno, module, names))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name, [alias.name]))
    return imports


def test_services_and_domain_layers_do_not_import_http_exceptions_or_status() -> None:
    """Verify services, application, and domain layers do not depend on HTTP exceptions."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    src_app = repo_root / "src" / "app"

    checked_dirs = [src_app / "services", src_app / "application", src_app / "domain"]
    violations: list[str] = []

    for directory in checked_dirs:
        if not directory.exists():
            continue
        for py_file in directory.rglob("*.py"):
            for lineno, module, names in _collect_module_imports(py_file):
                if "HTTPException" in names:
                    violations.append(
                        f"{py_file.name}:{lineno} imports HTTPException from '{module}'"
                    )
                if "status" in names and ("fastapi" in module or "starlette" in module):
                    violations.append(f"{py_file.name}:{lineno} imports status from '{module}'")

    msg = "Layer violation (HTTPException/status in core layers):\n" + "\n".join(violations)
    assert not violations, msg


def test_services_and_application_layers_do_not_import_frameworks_or_lower_layers() -> None:
    """Verify services/application do not import sqlalchemy, starlette, boto3, infra, or api."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    src_app = repo_root / "src" / "app"

    forbidden_prefixes = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "boto3",
        "app.infrastructure",
        "app.api",
        "app.storage",
    )
    violations: list[str] = []

    for directory in (src_app / "services", src_app / "application"):
        if not directory.exists():
            continue
        for py_file in directory.rglob("*.py"):
            for lineno, module, _names in _collect_module_imports(py_file):
                if any(module.startswith(p) for p in forbidden_prefixes):
                    violations.append(f"{py_file.name}:{lineno} imports forbidden '{module}'")

    msg = "Services/Application layer violation:\n" + "\n".join(violations)
    assert not violations, msg


def test_domain_layer_has_zero_external_dependencies() -> None:
    """Verify domain layer has zero dependencies on frameworks, ORM, config, or other layers."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    domain_dir = repo_root / "src" / "app" / "domain"
    if not domain_dir.exists():
        return

    forbidden_prefixes = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "pydantic_settings",
        "app.services",
        "app.api",
        "app.infrastructure",
    )
    violations: list[str] = []

    for py_file in domain_dir.rglob("*.py"):
        for lineno, module, _ in _collect_module_imports(py_file):
            if any(module.startswith(p) for p in forbidden_prefixes):
                violations.append(f"{py_file.name}:{lineno} imports forbidden '{module}'")

    msg = "Domain layer violation:\n" + "\n".join(violations)
    assert not violations, msg


def test_api_layer_imports_infrastructure_only_in_deps() -> None:
    """Verify api controllers never import infrastructure directly, except in deps.py for DI."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    api_dir = repo_root / "src" / "app" / "api"
    if not api_dir.exists():
        return

    violations: list[str] = []
    for py_file in api_dir.glob("*.py"):
        if py_file.name == "deps.py":
            continue
        for lineno, module, _ in _collect_module_imports(py_file):
            if module.startswith("app.infrastructure"):
                violations.append(
                    f"{py_file.name}:{lineno} imports infrastructure '{module}' outside deps.py"
                )

    msg = "Presentation layer violation:\n" + "\n".join(violations)
    assert not violations, msg
