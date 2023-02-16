#/bin/python3

# Script to rapidly assess the effect that a code change has to a wide variety
# of datasets.
#
# It enables to compare the results of applying a test version of the binary
# to a set of QA datasets against the results produced by a reference version.
#
# Terminology:
# *Test case* refers to the artifacts obtained by applying a specific binary
# version to a specific QA dataset.
# *Test suite* refers to the set of test cases obtained from applying a specific
# binary version to all QA datasets.
# *QA project* refers to the folder containing a QA dataset and possibly
# related data.
# The *test suite identifier* is a sha1 and an additional index. The sha1
# identifies the binary version and the additional index allows to distinguish
# binaries that were generated form the same commit in a dirty repo
# (uncommitted changes).
#
# A folder for a test case is named in the following way:
#
#    <sha1>_<id>_<qaDatasetName>_<optionalDescription>
#
# <sha1> and <id> together form the test suite identifier, <qaDatasetName> is
# the name of the dataset converted to camel case, and <optionalDescription> is
# an optional description supplied by the user to make it easier to relate the
# test suits to the change that they test, e.g.,
#
#    1234567890_001_snowyHillside_increasedStepSizeTo42
#


import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from argparse import ArgumentParser
from itertools import chain

logging.basicConfig(level=logging.DEBUG)

#-----------------------------------------------------------------------------misc helpers
def subprocess_output(command: list[str]):
    """Return stdout of the command."""
    result = subprocess.run(command, capture_output=True)
    result.check_returncode()
    return result.stdout.decode('utf-8').strip()


def subprocess_check(command: list[str]):
    """Return True if the command was successful, False else"""
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def git(*args, repo: Path=None):
    command = ["git"]
    if repo is not None:
        command += ["-C", repo]
    command.extend(args)
    return subprocess_output(command)


def _contains_tiffs(path):
    files = chain(path.glob('*.tif'), path.glob('*.tiff'), path.glob('*.jpg'), path.glob('*.jpeg')) # TODO: collect extensions somewhere and iterate here if possible
    try: next(files);     return True
    except StopIteration: return False


def is_part_of_git_repo(path: Path):
    """Check if path leads to a directory that is inside/part of a git repo."""
    try:
        git("-C", path, "rev-parse", "--is-inside-work-tree")
        return True
    except subprocess.CalledProcessError:
        return False


def camel_case(s: str):
    components = re.split("_| |\.|-", s)
    print("components: ", str(components))
    return components[0] + "".join(c.title() for c in components[1:])


#----------------------------------------------------------------------------------classes
class QAProject():
    """Class that represents a QA project.

    It is initialized from a path to the QA project folder. This folder is
    assumed to contain a subfolder called 'Images' in which the dataset is
    stored as a set of images:
        DataFolder
          |
          +-Images
              |
              +-img-001.tiff
              |
              +-img-002.tiff
              |
              +-...
    """
    @classmethod
    def _get_image_path(cls, project_root: Path):
        """Return path to subfolder of the project that should contain the images."""
        return project_root / 'Images'

    @classmethod
    def check(cls, path: Path):
        """Check that the requirements of a QAProject are met."""
        if not path.is_dir():
            logging.debug(f"Not a project '{path}': not a folder.")
            return False

        images_path = cls._get_image_path(path)

        if not images_path.exists() or not images_path.is_dir():
            logging.debug(f"Not a project '{path}': missing folder '{images_path.name}'.")
            return False

        if not _contains_tiffs(images_path):
            logging.debug(f"Not a project '{images_path}': no images found.")
            return False

        return True

    def __new__(cls, path: Path):
        """Ensure that the requirements of a QAProject are met before creating an instance."""
        if not cls.check(path):
            raise ValueError(f"Could not create {cls} from '{path}': requirements not met.")
        return super().__new__(cls)

    def __init__(self, path: Path):
        self.path = path

    def name(self):
        return self.path.name


class Repo():
    """A class that exposes some git functionality."""
    def __init__(self, inside_repo: Path):
        if not inside_repo.is_dir(): # passed path to file inside of repo?
            inside_repo = inside_repo.parent
        assert(is_part_of_git_repo(inside_repo))
        self.repo = git("rev-parse", "--show-toplevel", repo=inside_repo)

    def path(self):
        return self.repo

    def _git(self, *args):
        return git(*args, repo=self.repo)

    def get_merge_base(self, commit1: str, commit2: str):
        return self._git("merge-base", commit1, commit2)

    def retrieve_sha_of_branch(self, branch: str):
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


#-------------------------------------------------------------------------specific helpers
SEPARATOR = '_'


def check_binary(binary: Path):
    """Sanity checks on the binary."""
    if not binary.exists():
        logging.critical(f"'{binary}' not found.")
        sys.exit(-1)

    if not os.access(binary, os.X_OK):
        logging.critical(f"'{binary}' is not executable")
        sys.exit(-1)

    if not is_part_of_git_repo(binary.parent):
        logging.critical(f"'{binary}' is not inside of any repo. " +
                          "It is assumed to reside inside the main code repo.")
        sys.exit(-1)

    # TODO: check touch time


def test_case_name_regex():
    """Returns a regex matching the individual components of a test caste name.

    Usage:
    >>> m = re.match(test_case_name_regex(), "1234567890_001_snowyHillside_increasedStepSizeTo42")
    >>> m.group(1)  = '1234567890'
    >>> m.group(2)  = '001'
    >>> m.group(3)  = 'snowyHillside'
    >>> m.group(4)  = 'increasedStepSizeTo42'
    """
    sha1 = fr"[^\W_]+" # [^\W_]: alphanumeric without underscore
    _id = fr"\d+"
    project_name = fr"[^\W_]+"              # [^\W_]: alphanumeric without underscore
    optional_user_description = fr"[^\W_]*" # [^\W_]: alphanumeric without underscore
    return re.compile(fr"({sha1}){SEPARATOR}({_id}){SEPARATOR}({project_name}){SEPARATOR}?({optional_user_description})")


def parse_test_case_name(name: str):
    """Returns a dict of the components of the test case name."""
    m = test_case_name_regex().match(name)
    return {"sha1" : m.group(1),
            "id" : m.group(2),
            "dataset_name" : m.group(3),
            "optional_description" : m.group(4)}


def is_test_case_name(s: str):
    """Check if s fits the test case name convention."""
    return bool(test_case_name_regex().match(s))


def increment_id(_id: str):
    """Return the next id as zero-padded, fixed-length string."""
    l = len(_id)
    mod = 10**l
    next_id = str((int(_id) + 1) % mod)
    if next_id == '0': # we start at 1
        next_id = '1'
    return "0" * (l - len(next_id)) + next_id


def find_highest_id(sha1: str, qa_project_root: Path):
    s = f"{sha1}_98_test"
    print("s: ", s)
    r = fr'(?<={sha1}{SEPARATOR})\d*(?={SEPARATOR})'
    m = re.search(r, s)
    print("highest id: ", m.group(0))
    #test_outcomes = qa_project_root.glob(sha1 + "*")
    #ms = (re.search(fr'(?<={sha1}{SEPARATOR})\d*(?={SEPARATOR})', x) for x in test_outcomes)
    #ids = (m.group(0) for m in ms)
    #print('ids: ', list(ids))
    ##print("test outcomes: ", list(test_outcomes))
    ## TODO: CONTINUE HERE


def create_test_folder_name(project: QAProject, qa_project_root: Path, optionalDescription: str = None):
    # TODO:
    # * get sha
    # * get next id
    # * return folder name



if __name__ == "__main__":
    parser = ArgumentParser(
       description = 'this is the rapid qa description'
    )

    parser.add_argument(
        "projects",
         help = "Path to the QA data projects."
    )

    parser.add_argument(
        "binary",
         help = "Path to the binary under investigation. It is assumed to be inside the code repo."
    )

    if len(sys.argv) < 2:
        parser.print_help()

    arguments = parser.parse_args()
    qa_projects_root = Path(arguments.projects)
    qa_projects = [QAProject(path) for path in qa_projects_root.iterdir() if QAProject.check(path)]
    logging.info(f"found {len(qa_projects)} QA projects: {[p.name() for p in qa_projects]}")

    binary = Path(arguments.binary)
    check_binary(binary)

    repo = Repo(binary.parent)
    logging.info(f"repo is '{repo.path()}'")

    head = repo.retrieve_sha_of_branch("HEAD")
    logging.debug(f"HEAD is at '{head}'")

    main_branch = repo.guess_main_branch()
    logging.debug(f"main branch '{main_branch}'")

    reference = repo.get_merge_base(main_branch, head)
    logging.debug(f"merge-base (HEAD, {main_branch}) '{reference}'")

    non_merge_commits_missing_on_reference = repo.commits_from_to(reference, head, "--no-merges")
    logging.debug(f"commits from merge-base to HEAD:{non_merge_commits_missing_on_reference}")


    # patch for commit

    # patches for commits

    # current patch (or is this a version of above?)

    # TODO CONTINUE HERE: retrieve merge base between two commits, get patches for each commit
    # TODO this script should be able to accept a reference sha (or guess a sensible default, like the last commit on master/main)
    #  results that were made with a version that is committed have the sha as id, those with patches have sha + an increasing number.

    #print(f"retrieved HEAD sha {head_sha}")



    # 1. (DONE) if not a repo(binary) -> error
    # 2. retrieve last common ancestor with master/main
    # 3. allow the user to pass a custom reference branch
