import helpers
import lazytp as ltp

import os
import pytest
import re
import subprocess
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
        command += ["-C", str(repo)]
    command.extend(args)
    return subprocess_output(command)


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


@pytest.fixture
def repo_dir(tmp_path):
    """Fixture that yields a temporary git repository."""
    repo = (tmp_path / 'repo')
    repo.mkdir()
    git('init', repo)
    git('commit', '--allow-empty', '-m', '"dummy commit"', repo=repo)
    return repo


echo_call_program = "echo $0 $@"


@pytest.fixture
def repo_with_executable(repo_dir):
    """Fixture that yields a repo with an executable."""

    def _impl(executable=echo_call_program):
        """Inner function to enable injecting different executables into the fixture."""
        executable_path = repo_dir / "app"
        with open(executable_path, 'w') as f:
            f.write(executable)
        os.chmod(executable_path, 0o700) # owner may read, write, or execute
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


def insert_dummy_config(path: Path):
    config_path = path / 'config.txt'
    with open(config_path, 'w') as f:
        f.write("I'm a dummy config file.")
    return config_path


@pytest.fixture
def environment_for_test_pipeline(repo_with_executable,
                                  qa_project_with_images,
                                  out_dir_with_qa_test_cases):
    """Fixture that yields a complete environment for test_pipeline.

    This comprises
     * `repo_path`   path to a git repo
     * `app_path`    path to a dummy test_pipeline app inside `repo`for introspection
     * `images_path` path to a folder with dummy images
     * `config_path` dummy path to a config file
     * `out_path`    dummy path to an output folder
    """
    repo_with_call_inspection_executable = repo_with_executable(echo_call_program)
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


#--------------------------------------------------------------test misc helpers
def test_camel_case_removes_all_forbidden_symbols():
    non_camel_case_string = "one_two.three_four five six-seven.height-nine"
    camel_case_string = "oneTwoThreeFourFiveSixSevenHeightNine"
    assert helpers.camel_case(non_camel_case_string) == camel_case_string


#----------------------------------------------------------------------test Repo
def test_repo_class_can_be_constructed_from_repo_path(repo_dir):
    helpers.Repo(repo_dir)


def test_repo_class_cannot_be_constructed_from_non_repo_path(tmp_path):
    with pytest.raises(helpers.Repo.NotARepoException):
        helpers.Repo(tmp_path)


#-----------------------------------------------------------------test_QAProject
def test_qa_project_class_can_be_created_when_layout_assumptions_are_met(environment_for_test_pipeline):
    helpers.QAProject(environment_for_test_pipeline['images_path'].parent)


def test_qa_project_class_cannot_be_created_when_images_directory_is_missing(tmp_path):
    with pytest.raises(helpers.QAProject.LayoutError):
        helpers.QAProject(tmp_path)


def test_qa_project_class_cannot_be_created_when_images_directory_contains_no_images(tmp_path):
    (tmp_path / 'images').mkdir()
    with pytest.raises(helpers.QAProject.LayoutError):
        helpers.QAProject(tmp_path)


#----------------------------------------------------------test specific helpers
def test_get_next_id_returns_the_correct_id(out_dir_with_qa_test_cases):
    assert helpers.get_next_id(out_dir_with_qa_test_cases) == '004' # highest existing id is '003'


def test_qa_test_case_names_are_correct_when_no_description_given():
    sha1 = '1234567890'
    _id = '001'
    project_name = 'snowy_Hillside'
    test_case_name = helpers.create_test_case_name(_id, sha1, project_name)
    assert test_case_name == '001_1234567890_snowyHillside'


def test_qa_test_case_names_are_correct_when_description_given():
    sha1 = '1234567890'
    _id = '001'
    project_name = 'snowy_Hillside'
    description = "increasedStepSizeTo42"
    test_case_name = helpers.create_test_case_name(_id, sha1, project_name, description)
    assert test_case_name == '001_1234567890_snowyHillside_increasedStepSizeTo42'


#-----------------------------------------------------------------------test ltp
def test_call_test_pipeline_executes_the_expected_command(environment_for_test_pipeline):
    env = environment_for_test_pipeline
    command_triggered = ltp.test_pipeline(app_path = env['app_path'],
                                          out_path = env['out_path'],
                                          config_path = env['config_path'],
                                          images_path = env['images_path'])

    expected_command = (f"{env['app_path']} -f {env['config_path']} -o {env['out_path']} " +
                         ' '.join(str(image_path) for image_path in env['images_path'].glob('*')))
    assert command_triggered == expected_command


def test_lazy_test_pipeline_reads_local_config(environment_for_test_pipeline):
    env = environment_for_test_pipeline
    os.chdir(env['config_path'].parent)

    result = ltp.lazy_test_pipeline(app_path = env['app_path'],
                                    out_path = env['out_path'],
                                    images_path = env['images_path'])

    expected_substring = '-f config.txt'
    assert expected_substring in result


def test_lazy_test_pipeline_creates_correct_output_folder(environment_for_test_pipeline):
    env = environment_for_test_pipeline

    result = ltp.lazy_test_pipeline(app_path = env['app_path'],
                                    out_path = env['out_path'],
                                    images_path = env['images_path'])

    expected_qa_project_name = helpers.camel_case(env['images_path'].parent.name)
    expected_id = '004' # previous highest id was 003
    all_correct_output_folders = env['out_path'].glob(f"{expected_id}*{expected_qa_project_name}")
    assert len(list(all_correct_output_folders)) == 1