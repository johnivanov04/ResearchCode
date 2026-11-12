"""Shared fixtures for the experiment harness tests.

Docker tests run when Docker and the sandbox image are available; set RC_REQUIRE_DOCKER=1
(as CI does) to make their absence a failure instead of a skip.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from rc_experiments.config import Config
from rc_experiments.sandbox import SANDBOX_IMAGE, DockerBackend, LocalBackend, docker_available, image_id


@pytest.fixture(scope="session")
def config() -> Config:
    return Config.load()


@pytest.fixture(scope="session")
def local_backend() -> LocalBackend:
    # Only trusted code (references, defective variants, fixtures written here) runs locally.
    return LocalBackend(trusted=True)


@pytest.fixture(scope="session")
def docker_backend(config: Config) -> DockerBackend:
    if not (docker_available() and image_id(SANDBOX_IMAGE)):
        if os.environ.get("RC_REQUIRE_DOCKER") == "1":
            pytest.fail("Docker and the sandbox image are required (RC_REQUIRE_DOCKER=1)")
        pytest.skip("Docker or the sandbox image is not available")
    return DockerBackend(config)


@pytest.fixture
def make_submission(tmp_path: Path) -> Callable[..., Path]:
    """Create a submission directory from {relative path: source text}."""
    counter = iter(range(1000))

    def make(files: dict[str, str]) -> Path:
        root = tmp_path / f"submission-{next(counter)}"
        for relative, text in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        root.mkdir(exist_ok=True)
        return root

    return make
