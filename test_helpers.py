import helpers

import pytest
import shutil
import subprocess
import time
from pathlib import Path

# TODO: test this
def subprocess_output(command: list[str]):
    """Return stdout of the command."""
    result = subprocess.run(command, capture_output=True)
    result.check_returncode()
    return result.stdout.decode('utf-8').strip()


# TODO: test this
def git(*args, repo: Path=None):
    command = ["git"]
    if repo is not None:
        command += ["-C", repo]
    command.extend(args)
    return subprocess_output(command)


@pytest.fixture
def tmp_repo(tmp_path):
    """Fixture that yields a temporary git repository."""
    git('init', tmp_path)
    return tmp_path


#----------------------------------------------------------------------test Repo
def test_repo_class_can_be_constructed_from_repo_path(tmp_repo):
    helpers.Repo(tmp_repo)


def test_repo_class_cannot_be_constructed_from_non_repo_path(tmp_path):
    with pytest.raises(helpers.Repo.NotARepoException):
        helpers.Repo(tmp_path)