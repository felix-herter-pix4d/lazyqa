import common

from pathlib import Path
import configparser
import os
import pytest
import subprocess


content_of = common.content_of
write_file = common.write_file


def skip_on_windows(f):
    """Decorator that can be used to skip tests that don't run under windows."""
    import os
    if os.name == 'nt':
        return pytest.mark.skip(f)
    return f



def subprocess_output(command: list[str]):
    """Return stdout of the command."""
    result = subprocess.run(command, capture_output=True)
    try:
        result.check_returncode()
    except subprocess.CalledProcessError as err:
        print(f"subprocess: '{command}' raised {err}\nstdout: {result.stderr.decode('utf-8').strip()}")
        raise err
    return result.stdout.decode('utf-8').strip()


echo_call_program = "echo $0 $@"


def git(*args, repo: Path=None):
    command = ["git"]
    if repo is not None:
        command += ["-C", str(repo)]
    command.extend(args)
    return subprocess_output(command)


@pytest.fixture
def repo_dir(tmp_path):
    """Fixture that yields a temporary git repository."""
    repo = (tmp_path / 'repo')
    repo.mkdir()
    git('init', repo)
    git('commit', '--allow-empty', '-m', '"dummy commit"', repo=repo)
    return repo


@pytest.fixture
def repo_with_executable(repo_dir):
    """Fixture that yields a repo with an executable."""

    def _impl(repo=repo_dir, executable=echo_call_program):
        """Inner function to enable injecting different repos or executables."""
        executable_path = repo_dir / "app"
        with open(executable_path, 'w') as f:
            f.write(executable)
        os.chmod(executable_path, 0o700) # owner may read, write, or execute
        git('add', '.', repo=repo)
        git('commit', '-m', '"added executable"', repo=repo)
        return {'repo': repo_dir, 'executable': executable_path}

    yield _impl


def insert_dummy_images(path: Path):
    for img in ['img_01.TIF', 'img_02.TIF']:
        (path / img).touch()


@pytest.fixture
def qa_project_with_images(tmp_path):
    """Fixture that yields a QA project with subdirectory 'images' that contains dummy images."""
    qa_project_path = tmp_path / 'snowy_hillside'
    images_path = qa_project_path / 'images'
    images_path.mkdir(parents=True, exist_ok=True)
    insert_dummy_images(images_path)
    yield {'qa_project_path': qa_project_path, 'images_path': images_path}


@pytest.fixture
def out_dir_with_qa_test_cases(tmp_path):
    """Fixture that yields a directory with some folders inside.

    Specifically there are folders
    * 001_1234_project1_userDescription
    * 003_1234_project1_userDescription
    """
    out_path = (tmp_path / 'Output')
    for directory_name in ('001_1234_project1_userDescription',
                           '003_1234_project1_userDescription'):
        (out_path / directory_name).mkdir(parents=True, exist_ok=True)
    yield out_path


def insert_dummy_config(path: Path):
    config_path = path / 'config.ini'
    content = '[section1]\nkey1 = value1\nkey2 = value2\n\n[section2]\nkey3 = value3' # whitespaces as in the config generated by lazy_test_ortho
    with open(config_path, 'w') as f:
        f.write(content)
    return config_path


@pytest.fixture
def make_environment_for_test_pipeline(repo_with_executable,
                                       qa_project_with_images,
                                       out_dir_with_qa_test_cases):
    """Fixture that yields a complete environment for test_pipeline.

    This comprises
     * `repo_path`   Path to a git repo.
     * `app_path`    Path to a dummy test_pipeline app inside `repo`for introspection.
                     The app is a dummy that returns the call with which it was invoked
                     to allow inspecting if the arguments passed to the app are correct.
     * `images_path` Path to a folder with dummy images.
     * `config_path` Path to a config file.
     * `out_path`    Path to an output folder.
    """
    def environment_for_test_pipeline(executable = echo_call_program):
        """The actual fixture. Allows altering the environment as needed."""
        repo_with_call_inspection_executable = repo_with_executable(executable=executable)
        repo_path = repo_with_call_inspection_executable['repo']
        app_path = repo_with_call_inspection_executable['executable']
        images_path = qa_project_with_images['images_path']
        config_path = insert_dummy_config(repo_path.parent)
        out_path = out_dir_with_qa_test_cases
        return {'repo_path': repo_path,
                'app_path': app_path,
                'images_path': images_path,
                'config_path': config_path,
                'out_path': out_path}
    return environment_for_test_pipeline


def config_subset(config_1: str, config_2: str):
    """Check if the config config_1 is a subset of config_2.

    Sometimes we cannot check for equality due to whitespace differences in the
    string representation or because one configuration is a subset of the other.
    """
    parser_1 = configparser.ConfigParser(); parser_1.read_string(config_1)
    parser_2 = configparser.ConfigParser(); parser_2.read_string(config_2)
    sections_1 = set(parser_1.sections())
    sections_2 = set(parser_2.sections())

    if not sections_1.issubset(sections_2):
        return False
    for section in sections_1:
        if not parser_1[section].items() <= parser_2[section].items():
            return False
    return True