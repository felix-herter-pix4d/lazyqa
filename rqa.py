#/bin/python3

# Script to rapidly assess the effect that a code change has to a wide variety
# of test cases (QA datasets).
#
# It enables to compare the *new* results produced by the app with a
# *reference* output (usually produced the current state of the app).
#
# Notes: The terms QA datasets and QA projects are used interchangeably and
# refer, depending on the context, to the set of images that belong to one
# project or the folder containing all information for the project, including
# the images).

import sys
import os
import logging
import subprocess
from pathlib import Path
from argparse import ArgumentParser
from itertools import chain

logging.basicConfig(level=logging.DEBUG)


def _contains_tiffs(path):
    files = chain(path.glob('*.tif'), path.glob('*.tiff'), path.glob('*.jpg'), path.glob('*.jpeg')) # TODO: collect extensions somewhere and iterate here if possible
    try: next(files);     return True
    except StopIteration: return False


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
        logging.info(f"Created QAProject:{path=}")
        self.path = path


def subprocess_output(command: list[str]):
    result = subprocess.run(command, capture_output=True)
    return result.stdout.decode('utf-8').strip()


def subprocess_check(command: list[str]):
    """Return True if the command was successful, False else"""
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def is_part_of_git_repo(path: Path):
    try:
        subprocess.run(["git", "-C", f"{binary.parent}", "rev-parse", "--is-inside-work-tree"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def get_merge_base(commit1: str, commit2: str, repo: Path):
    return subprocess_output(["git", "-C", f"{binary.parent}", "merge-base", commit1, commit2])


def retrieve_sha_of_branch(branch: str, repo: Path):
    return subprocess_output(["git", "-C", f"{repo}", "rev-parse", f"{branch}"])


def guess_main_branch(repo: Path):
    """Guess if 'master' or 'main' is used as main development branch."""
    # We did not use `git ls-remote --heads origin ...` to avoid fetching the repo (slow)
    try:
        subprocess.run(["git", "-C", repo, "show-branch", "origin/master"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True )
        return "master"
    except subprocess.CalledProcessError:
        try:
            subprocess.run(["git", "-C", repo, "show-branch", "origin/main"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True )
            return "main"
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Could not guess main branch in repo '{repo}'")


def is_ancestor(commit1: str, commit2: str, repo: Path):
    return subprocess_check(["git", "-C", f"{repo}", "merge-base", "--is-ancestor", commit1, commit2])


def commits_from_to(commit1: str, commit2: str, repo: Path):
    """Retrieve sequence of commits from commit1 (exclusive) to commit2 (inclusive)."""
    if not is_ancestor(commit1, commit2, repo):
        raise RuntimeError(f"asked for commits from '{commit1}' to '{commit2}' but the first is not an ancestor of the second")
    return subprocess_output(["git", "-C", f"{repo}", "log", "--format=format:%H", f"{commit1}..{commit2}"]).split()


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
    qa_projects = (QAProject(path) for path in qa_projects_root.iterdir() if QAProject.check(path))

    binary = Path(arguments.binary)
    check_binary(binary)

    head = retrieve_sha_of_branch("HEAD", binary.parent)
    logging.debug(f"HEAD is at '{head}'")

    main_branch = guess_main_branch(binary.parent)
    logging.debug(f"main branch '{main_branch}'")

    reference = get_merge_base(main_branch, head, binary.parent)
    logging.debug(f"merge base head-master '{reference}'")

    commits_missing_on_reference = commits_from_to(reference, head, binary.parent)
    logging.debug(f"commits from merge-base to HEAD:{commits_missing_on_reference}")



