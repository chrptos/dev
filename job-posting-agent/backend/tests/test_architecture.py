"""層の向き（docs/backend-architecture.md）を確かめる。"""

import ast
import shutil
import subprocess
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PACKAGE = BACKEND / "src" / "job_posting_agent"


def test_import_contracts_are_kept() -> None:
    """pyproject.toml の [tool.importlinter] の決まりを守っている。"""
    lint_imports = shutil.which("lint-imports")
    assert lint_imports is not None, "import-linter が入っていません（uv sync）"
    result = subprocess.run(  # noqa: S603 - 固定のコマンドを実行するだけ
        [lint_imports, "--no-cache"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _imported_modules(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def test_only_infrastructure_touches_adk_runner_and_sessions() -> None:
    """ADK の Runner とセッションに触るのは infrastructure/adk/ だけ。"""
    forbidden = ("google.adk.runners", "google.adk.sessions")
    allowed_dir = PACKAGE / "infrastructure" / "adk"
    violations = [
        f"{path.relative_to(PACKAGE)}: {name}"
        for path in PACKAGE.rglob("*.py")
        if allowed_dir not in path.parents and path.name not in ("main.py",)
        for name in _imported_modules(path)
        if name.startswith(forbidden)
    ]
    assert violations == []
