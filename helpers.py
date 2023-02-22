import logging
import re
import subprocess
from pathlib import Path


#-------------------------------------------------------------------misc helpers
def camel_case(s: str):
    """Turn s into camel case, removing any of the symbols in '_ .-'"""
    components = re.split("_| |\.|-", s)
    return components[0] + "".join(c.title() for c in components[1:])


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


#---------------------------------------------------------------------------Repo
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

    def get_sha_of_branch(self, branch: str, short: bool=False):
        sha1 = self._git("rev-parse", branch)
        if short:
            sha1 = self.get_short_sha1(sha1)
        return sha1

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


#----------------------------------------------------------------------QAProject
#TODO: do we need this? What should it do?
class QAProject():
    """Class that represents a QA project.

    It is initialized from a path to the QA project folder that fulfills the
    following layout assumptions: There is a subfolder 'images' in which the
    dataset is stored as a set of images:

        DataFolder
          |
          +-images
              |
              +-img-001.tiff
              |
              +-img-002.tiff
              |
              +-...
    """
    class LayoutError(Exception):
        """Some assumptions about the directory layout are not fulfilled."""
        pass

    @staticmethod
    def _contains_tiffs(path):
        from itertools import chain
        image_extensions = ('tif', 'TIF', 'tiff', 'TIFF', 'jpg', 'JPG', 'jpeg', 'JPEG')
        files = chain(*(path.glob(f'*.{extension}') for extension in image_extensions))
        try: next(files);     return True
        except StopIteration: return False

    @classmethod
    def _get_image_path(cls, project_root: Path):
        """Return path to subfolder of the project that should contain the images."""
        return project_root / 'images'

    @classmethod
    def check(cls, path: Path):
        """Check that the requirements of a QAProject are met."""
        if not path.is_dir():
            raise cls.LayoutError(f"directory '{path}' not found.")

        images_path = cls._get_image_path(path)
        if not images_path.exists() or not images_path.is_dir():
            raise cls.LayoutError(f"'{path}' missing folder '{images_path.name}'.")

        if not cls._contains_tiffs(images_path):
            raise cls.LayoutError(f"no images found in '{images_path.name}'.")

    def __new__(cls, path: Path):
        """Ensure that the requirements of a QAProject are met before creating an instance."""
        cls.check(path)
        return super().__new__(cls)

    def __init__(self, path: Path):
        self.path = path

    def name(self):
        return self.path.name


#-------------------------------------------------------------------------specific helpers
SEPARATOR = '_'
ID_LEN = 3 # length of the id component in the test case name, e.g. 005


def test_case_name_regex():
    """Returns a regex matching the individual components of a test caste name.

    Usage:
    >>> m = re.match(test_case_name_regex(), "001_1234567890_snowyHillside_increasedStepSizeTo42")
    >>> m.group(1)  = '001'
    >>> m.group(2)  = '1234567890'
    >>> m.group(3)  = 'snowyHillside'
    >>> m.group(4)  = 'increasedStepSizeTo42'
    """
    _id = fr"\d+"
    sha1 = fr"[^\W_]+" # [^\W_]: alphanumeric without underscore
    project_name = fr"[^\W_]+"              # [^\W_]: alphanumeric without underscore
    optional_user_description = fr"[^\W_]*" # [^\W_]: alphanumeric without underscore
    return re.compile(fr"({_id}){SEPARATOR}({sha1}){SEPARATOR}({project_name}){SEPARATOR}?({optional_user_description})")


def parse_test_case_name(name: str):
    """Returns a dict of the components of the test case name."""
    m = test_case_name_regex().match(name)
    return {"id" : m.group(1),
            "sha1" : m.group(2),
            "dataset_name" : m.group(3),
            "optional_description" : m.group(4)}


def is_test_case_name(s: str):
    """Check if s fits the test case name convention."""
    return bool(test_case_name_regex().match(s))


def create_test_case_name(_id: str, sha1: str, project_name: str, optional_description: str = None):
    result =  _id + SEPARATOR + sha1 + SEPARATOR + camel_case(project_name)
    if optional_description is not None:
        result += '_' + camel_case(optional_description)
    return result


def increment_id(_id: str):
    """Return the next id as zero-padded, fixed-length string."""
    mod = 10**ID_LEN
    next_id = str((int(_id) + 1) % mod)
    if next_id == '0': # we start at 1
        next_id = '1'
    return '0' * (ID_LEN - len(next_id)) + next_id


def find_highest_id(qa_project_root: Path):
    project_names = (path.name for path in qa_project_root.glob("*") if is_test_case_name(path.name))
    ids = {parse_test_case_name(name)['id'] for name in project_names}
    zero_id = '0' * ID_LEN
    return zero_id if not ids else max(ids)


def get_next_id(qa_project_root: Path):
    return increment_id(find_highest_id(qa_project_root))