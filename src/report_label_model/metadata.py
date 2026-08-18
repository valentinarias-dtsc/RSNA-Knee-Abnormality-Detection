"""Hashes and environment capture for reproducible Stage 04 runs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
from typing import Iterable, Mapping


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_state(root: Path) -> dict[str, object]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True,
        ).stdout.strip())
        return {"commit_sha": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit_sha": None, "dirty": None}


def package_versions(names: Iterable[str]) -> dict[str, str | None]:
    output: dict[str, str | None] = {}
    for name in names:
        try:
            output[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            output[name] = None
    return output


def file_manifest(paths: Iterable[Path], root: Path) -> dict[str, dict[str, object]]:
    output = {}
    for path in sorted({value.resolve() for value in paths if value.exists()}):
        try:
            portable = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            portable = str(path)
        output[portable] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return output


def checkpoint_manifest(checkpoint_dir: Path, root: Path) -> dict[str, object]:
    files = [path for path in checkpoint_dir.rglob("*") if path.is_file()] if checkpoint_dir.exists() else []
    return {
        "checkpoint_dir": checkpoint_dir.resolve().relative_to(root.resolve()).as_posix()
        if checkpoint_dir.exists() else checkpoint_dir.as_posix(),
        "files": file_manifest(files, root),
    }


def base_run_metadata(
    root: Path,
    config_path: Path,
    input_paths: Mapping[str, Path],
    seed: int,
    stage_version: str,
    upstream_policy_version: str,
) -> dict[str, object]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git": git_state(root),
        "stage_version": stage_version,
        "upstream_policy_version": upstream_policy_version,
        "seed": int(seed),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "packages": package_versions((
            "pandas", "numpy", "matplotlib", "torch", "transformers", "scikit-learn",
        )),
        "config": {"path": str(config_path), "sha256": sha256_file(config_path)},
        "inputs": {
            name: {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in input_paths.items()
        },
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

