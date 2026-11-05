import tomllib
from pathlib import Path

import src


def test_scaffold_metadata() -> None:
    root = Path(__file__).resolve().parent.parent
    pyproject_path = root / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml must exist"

    config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    assert config["project"]["name"] == "finago-ai-copilot"
    assert src.__version__ == "0.1.0"
    assert (root / "Dockerfile").exists()
    assert (root / "docker-compose.yml").exists()
    assert (root / "PLAN.md").exists()
