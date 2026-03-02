#!/usr/bin/env python
"""Fail when runtime dependencies use GPL-family licenses."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


BLOCKED_LICENSE_RE = re.compile(r"\b(?:GPL|AGPL|LGPL)\b", re.IGNORECASE)
RUNTIME_REQUIREMENT_FILES = ("requirements.txt",)
PYPROJECT_FILE = "pyproject.toml"


def normalize_package_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def parse_requirement_name(spec: str) -> str | None:
    trimmed = spec.strip()
    if not trimmed or trimmed.startswith("#"):
        return None
    if trimmed.startswith(("-", "--")):
        return None

    candidate = trimmed.split("#", 1)[0].strip()
    candidate = candidate.split(";", 1)[0].strip()
    candidate = candidate.split("[", 1)[0].strip()
    for separator in ("===", "==", ">=", "<=", "~=", "!=", ">", "<"):
        if separator in candidate:
            candidate = candidate.split(separator, 1)[0].strip()
            break
    if not candidate:
        return None
    return normalize_package_name(candidate)


def load_runtime_dependencies(repo_root: Path) -> list[str]:
    dependencies: set[str] = set()

    pyproject_path = repo_root / PYPROJECT_FILE
    if pyproject_path.exists():
        pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

        project_dependencies = pyproject_data.get("project", {}).get("dependencies", [])
        for dependency in project_dependencies:
            parsed = parse_requirement_name(str(dependency))
            if parsed:
                dependencies.add(parsed)

        poetry_dependencies = (
            pyproject_data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        )
        if isinstance(poetry_dependencies, dict):
            for package_name in poetry_dependencies:
                normalized = normalize_package_name(str(package_name))
                if normalized != "python":
                    dependencies.add(normalized)

    for requirements_file in RUNTIME_REQUIREMENT_FILES:
        requirements_path = repo_root / requirements_file
        if requirements_path.exists():
            for line in requirements_path.read_text(encoding="utf-8").splitlines():
                parsed = parse_requirement_name(line)
                if parsed:
                    dependencies.add(parsed)

    return sorted(dependencies)


def load_installed_licenses() -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, "-m", "piplicenses", "--format=json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        detail = stderr or result.stdout.strip() or "Unknown pip-licenses error"
        raise RuntimeError(
            "Failed to execute pip-licenses. Install it with "
            "`python -m pip install pip-licenses`.\n"
            f"Details: {detail}"
        )

    try:
        entries = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unable to parse pip-licenses output: {exc}") from exc

    licenses: dict[str, str] = {}
    for entry in entries:
        package = normalize_package_name(str(entry.get("Name", "")))
        if not package:
            continue
        licenses[package] = str(entry.get("License", "UNKNOWN"))
    return licenses


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    runtime_dependencies = load_runtime_dependencies(repo_root)

    if not runtime_dependencies:
        print("No runtime dependency manifest found; GPL check skipped.")
        return 0

    try:
        installed_licenses = load_installed_licenses()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1

    blocked: list[tuple[str, str]] = []
    for dependency in runtime_dependencies:
        license_name = installed_licenses.get(dependency)
        if license_name and BLOCKED_LICENSE_RE.search(license_name):
            blocked.append((dependency, license_name))

    if blocked:
        print("ERROR: Copyleft license detected in runtime dependencies:")
        for dependency, license_name in blocked:
            print(f"- {dependency}: {license_name}")
        print("Remove or replace GPL/AGPL/LGPL dependencies.")
        return 1

    print("GPL license check passed for runtime dependencies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
