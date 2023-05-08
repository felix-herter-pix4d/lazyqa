import configparser
import datetime
import os
import re
import sys
import subprocess
import time
from pathlib import Path


#--------------------------------------------------------------------------------constants
# constants that are used throughout the different modules

SEPARATOR = '_' # separator to distinguish the different components of a name
                # (folder name or file name, often also referred to as test case name)
ID_LEN = 3 # length of the id component (increasing number) to enumerate the
           # different outputs of different invocations of one of the scripts.


#-------------------------------------------------------------------misc helpers
# heper functionality that is rather general

def camel_case(s: str) -> str:
    """Turn s into camel case, removing any of the symbols in '_ .-'"""
    components = re.split("_| |\.|-", s)
    return components[0] + "".join(c.title() for c in components[1:])


def parse_config(config:str) -> configparser.ConfigParser:
    """Return a ConfigParser that parsed the config; the parser is case-sensitive wrt the keys."""
    parser = configparser.ConfigParser()
    parser.optionxform = str # our keys are case-sensitive, see https://stackoverflow.com/questions/1611799/preserve-case-in-configparser
    parser.read_string(config)
    return parser


def content_of(file: Path) -> str:
    """Return the content of the file."""
    result = None
    with open(file) as f:
        result = f.read().strip()
    return result


def write_file(content:str, file_path: Path) -> None:
    """Write the string to a (newly created) file at path."""
    with open(file_path, 'w') as f:
        f.write(content)


def sanitize_command(command: str | list[str]) -> str | list[str]:
    """Sanitize all components of the command.

    * Explands tilde to the user's home directory. E.g. ['ls', '~'] -> ['ls', '/home/<username>/']
      where <username> is the actual username.
    """
    sanitize = lambda x : os.path.expanduser(x) if issubclass(type(x), Path) else x
    if issubclass(type(command), list):
        return [sanitize(component) for component in command]
    else: # no list, hopefully string or Path
        return sanitize(command)


def execute_command(command: list[str],
                    out_file: Path = None, # where to store the stdout (and stderr)
                    live_output: bool = False # command's stdout to screen
                    ) -> str:
    """Execute a command in a shell, print stdout to screen, to a file, or to both.

    Returns the stdout of the command.
    """
    if os.name == 'nt': # on windows, use 'powershell' instead of the default 'cmd'
        os.environ['COMSPEC'] = 'powershell'

    process = subprocess.Popen(sanitize_command(command),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               encoding='utf-8',
                               shell=True)
    output_lines = []
    file = open(out_file, 'w+') if out_file is not None else None

    for line in iter(process.stdout.readline, ''):
        if live_output:
            print(line, end='')
        if file is not None:
            file.write(line)

        output_lines.append(line.strip())

    if file is not None:
        file.close()

    return '\n'.join(output_lines)


def subprocess_output(command: list[str]) -> str:
    """Return stdout of the command."""
    result = subprocess.run(sanitize_command(command), capture_output=True)
    result.check_returncode()
    return result.stdout.decode('utf-8').strip()


def git(*args, repo: Path=None) -> str:
    """Call a git command with specified arguments, possibly from outside the repo."""
    command = ["git"]
    if repo is not None:
        command += ["-C", repo]
    command.extend(args)
    return subprocess_output(command)


def is_part_of_git_repo(path: Path) -> bool:
    """Check if path leads to a directory that is inside/part of a git repo."""
    if not path.is_dir():
        path = path.parent
    try:
        git("-C", path, "rev-parse", "--is-inside-work-tree")
        return True
    except subprocess.CalledProcessError:
        return False


class colors:
    red = '\033[91m'
    orange = '\033[93m'
    normal = '\033[0m'


def check_executable(app_path: Path, recompile: bool = True, prompt_user_confirmation: bool = True) -> None:
    """Do some checks for the executable `app_path`.

    Re-compile to make sure that we are working with an up-to-date version.
    If the executable is old -> prompt for user confirmation to still use it.

    app_path:                 Path to the executable.
    recompile:                If false, skip the re-compilation and use the binary, as is.
    prompt_user_confirmation: If false, do not ask the user to confirm when attempting to use
                              stale executables.
    """
    # path points to nowhere?
    if not app_path.exists():
        print(f'{colors.red}',
              f'binary {app_path} not found',
              f'{colors.normal}')
        exit(-1)

    # binary accidentally a directory?
    if app_path.is_dir():
        print(f'{colors.red}',
              f'binary {app_path} is actually a directory',
              f'{colors.normal}')
        exit(-1)

    # binary not executable?
    if not os.access(app_path, os.X_OK):
        print(f'{colors.red}',
              f'binary {app_path} is not executable',
              f'{colors.normal}')
        exit(-1)

    # binary not part of git repo?
    if not is_part_of_git_repo(app_path):
        print(f'{colors.red}',
              f'binary {app_path} must be inside the repo',
              f'{colors.normal}')
        exit(-1)

    # recompile test_ortho
    if recompile:
        print(f're-compiling {app_path.name}...')
        execute_command(f'cmake --build {app_path.parent.parent} -t {app_path.name}', live_output = True)

    # stale binary?
    if prompt_user_confirmation:
        seconds_since_last_modification =  int(time.time() - os.path.getmtime(app_path))
        if seconds_since_last_modification > 60:
            print(f'{colors.orange}age:',
                  f'{datetime.timedelta(seconds=seconds_since_last_modification)}',
                  f'{colors.normal}')
            input('(press any key to continue)')


#---------------------------------------------------------------------------Repo
class Repo():
    """A class that represents a git repository and exposes some handy git functionality.

    All git commands are affecting the represented repository.
    """

    repo: Path # path to the repo on which the git commands shall have effect.

    class NotARepoException(Exception):
        pass

    def __init__(self, path_into_repo: Path) -> None:
        if not path_into_repo.is_dir(): # passed path to file inside of repo?
            path_into_repo = path_into_repo.parent
        if not is_part_of_git_repo(path_into_repo):
            raise self.NotARepoException(f"Path '{path_into_repo}' must lead into a git repo.")
        self.repo = git("rev-parse", "--show-toplevel", repo=path_into_repo)

    def path(self) -> Path:
        """Return path to the repo."""
        return self.repo

    def _git(self, command: str) -> str:
        """Execute git command on this repo, return stdout(or stderr)."""
        return git(*command.split(), repo=self.repo)

    def get_merge_base(self, commit1: str, commit2: str) -> str:
        """Return sha1 of last common ancestor between the two commits."""
        return self._git(f'merge-base {commit1} {commit2}')

    def get_sha_of_branch(self, branch: str, short: bool=False) -> str:
        """Return sha1 on the given branch."""
        sha1 = self._git(f'rev-parse {branch}')
        if short:
            sha1 = self.get_short_sha1(sha1)
        return sha1

    def get_short_sha1(self, sha1: str) -> str:
        """Return short version of the sha1."""
        return self._git(f'rev-parse --short {sha1}')

    def guess_main_branch(self) -> str:
        """Guess if 'master' or 'main' is used as main development branch."""
        # `git ls-remote --heads origin ...` would fetch the repo, which takes too long
        for guess in ('origin/master', 'origin/main', 'master', 'main'):
            try:
                self._git(f'show-branch {guess}')
                return f'{guess}'
            except subprocess.CalledProcessError:
                pass
        raise RuntimeError(f"Could not guess main branch in repo '{self.repo}'")

    def get_patch(self, _from: str, to: str='HEAD') -> str:
        """Get the patch of changes between the two commits _from and to."""
        return self._git(f'format-patch {_from}..{to} --stdout')

    def get_untracked_changes(self) -> str:
        """Return a patch of the untracked changes.

        If new files should be included in the patch, as well, this function
        needs to be adjusted.
        """
        patch = self._git('diff')
        return patch


#-------------------------------------------------------------------------specific helpers
# helper functionality that is more specific to the domain

def add_patch_not_on_main_branch(repo: Repo, out_path: Path, patch_name: str = 'notOnMainBranch.patch') -> None:
    """Add patch-file containing the changes that are not on the main branch.

    repo:       Repository from which the patch is generated.
    out_path:   Path to the output folder.
    patch_name: Filename of the file containing the patch.
    """
    patch_not_on_main_branch = repo.get_patch(_from=repo.get_merge_base('HEAD', repo.guess_main_branch()))
    if patch_not_on_main_branch:
        with open(out_path / patch_name, 'w') as patch_file:
            patch_file.write(patch_not_on_main_branch)


def add_patch_dirty_state(repo: Repo, out_path: Path, patch_name: str = 'dirtyState.patch') -> None:
    """Add a patch-file to out_path containing the untracked changes of the repo.

    repo:       Repository from which the patch is generated.
    out_path:   Path to the output folder.
    patch_name: Filename of the file containing the patch.
    """
    untracked_patch = repo.get_untracked_changes()
    if untracked_patch:
        with open(out_path / patch_name, 'w') as patch_file:
            patch_file.write(untracked_patch)


def test_case_name_regex() -> re.Pattern:
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


def parse_test_case_name(name: str) -> dict:
    """Returns a dict of the components of the test case name."""
    m = test_case_name_regex().match(name)
    return {"id" : m.group(1),
            "sha1" : m.group(2),
            "dataset_name" : m.group(3),
            "optional_description" : m.group(4)}


def is_test_case_name(s: str) -> bool:
    """Check if s fits the test case name convention."""
    return bool(test_case_name_regex().match(s))


def create_test_case_name(_id: str, sha1: str, project_name: str, optional_description: str = None) -> str:
    """Combine the individual components to a test case name."""
    result =  _id + SEPARATOR + sha1 + SEPARATOR + camel_case(project_name)
    if optional_description is not None:
        result += '_' + camel_case(optional_description)
    return result


def increment_id(_id: str) -> str:
    """Return the next id as zero-padded, fixed-length string."""
    mod = 10**ID_LEN
    next_id = str((int(_id) + 1) % mod)
    if next_id == '0': # we start at 1
        next_id = '1'
    return '0' * (ID_LEN - len(next_id)) + next_id


def find_highest_id(folder: Path) -> str:
    """Find the highest id that is currently in use in the folder."""
    project_names = (path.name for path in folder.glob("*") if is_test_case_name(path.name))
    ids = {parse_test_case_name(name)['id'] for name in project_names}
    zero_id = '0' * ID_LEN
    return zero_id if not ids else max(ids)


def get_next_id(folder: Path) -> str:
    """Return the next id to be used for adding a new test case result to the specified folder."""
    return increment_id(find_highest_id(folder))
