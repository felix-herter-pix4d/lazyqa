import subprocess
from pathlib import Path

def subprocess_output(command: list[str]):
    """Return stdout of the command."""
    result = subprocess.run(command, capture_output=True)
    result.check_returncode()
    return result.stdout.decode('utf-8').strip()


def git(*args, repo: Path=None):
    command = ["git"]
    if repo is not None:
        command += ["-C", repo]
    command.extend(args)
    return subprocess_output(command)


def is_part_of_git_repo(path: Path):
    """Check if path leads to a directory that is inside/part of a git repo."""
    try:
        git("-C", path, "rev-parse", "--is-inside-work-tree")
        return True
    except subprocess.CalledProcessError:
        return False

class Repo():
    """A class that exposes some git functionality."""
    class NotARepoException(Exception):
        pass

    def __init__(self, path_into_repo: Path):
        if not path_into_repo.is_dir(): # passed path to file inside of repo?
            path_into_repo = path_into_repo.parent
        if not is_part_of_git_repo(path_into_repo):
            raise self.NotARepoException(f"Path '{path_into_repo}' must lead into a git repo.")
        self.repo = git("rev-parse", "--show-toplevel", repo=path_into_repo)

    def path(self):
        return self.repo

    def _git(self, *args):
        return git(*args, repo=self.repo)

    def get_merge_base(self, commit1: str, commit2: str):
        return self._git("merge-base", commit1, commit2)

    def get_sha_of_branch(self, branch: str):
        return self._git("rev-parse", branch)

    def get_short_sha1(self, sha1: str):
        return self._git("rev-parse", "--short", sha1)

    def guess_main_branch(self):
        """Guess if 'master' or 'main' is used as main development branch."""
        # We did not use `git ls-remote --heads origin ...` to avoid fetching the repo (slow)
        try:
            self._git("show-branch", "origin/master")
            return "master"
        except subprocess.CalledProcessError:
            try:
                self._git("show-branch", "origin/main")
                return "main"
            except subprocess.CalledProcessError:
                raise RuntimeError(f"Could not guess main branch in repo '{repo}'")

    def is_ancestor(self, commit1: str, commit2: str):
        return subprocess_check(["git", "-C", f"{self.repo}", "merge-base", "--is-ancestor", commit1, commit2])

    def commits_from_to(self, commit1: str, commit2: str, *args):
        """Retrieve sequence of commits from commit1 (exclusive) to commit2 (inclusive)."""
        assert(self.is_ancestor(commit1, commit2))
        command =  ("--format=format:%H", f"{commit1}..{commit2}")
        return self._git("log", *args, *command).split()

