# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import annotations

import ast
from pathlib import Path


VIBECAD_DIR = Path(__file__).resolve().parent.parent
TOOL_IMPL = VIBECAD_DIR / "tool_impl"
GENERIC_HOST_MODULES = (
    TOOL_IMPL / "analysis_contracts.py",
    TOOL_IMPL / "analysis_artifacts.py",
    TOOL_IMPL / "analysis_runtime.py",
    TOOL_IMPL / "analysis_local_provider.py",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "FreeCAD",
    "FreeCADGui",
    "Fem",
    "fem",
    "VibeCADAero",
    "VibeCADNativeAnalyze",
    "tool_impl.analysis_fem_adapter",
)


def _imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return tuple(imported)


def test_generic_host_analysis_modules_do_not_import_cad_or_domain_layers() -> None:
    violations: list[str] = []
    for path in GENERIC_HOST_MODULES:
        assert path.is_file(), f"missing generic host module: {path.name}"
        for imported in _imported_modules(path):
            if imported.startswith(FORBIDDEN_IMPORT_PREFIXES):
                violations.append(f"{path.name}: {imported}")

    assert violations == [], (
        "Generic host Analysis modules must remain domain-neutral and must not "
        "depend on live CAD/native analysis layers: " + ", ".join(violations)
    )
