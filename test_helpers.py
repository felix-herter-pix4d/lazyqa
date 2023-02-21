import helpers
import rtp

import os
import pytest
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
        command += ["-C", repo]
    command.extend(args)
    return subprocess_output(command)


@pytest.fixture
def tmp_repo(tmp_path):
    """Fixture that yields a temporary git repository."""
    git('init', tmp_path)
    return tmp_path


echo_call_program = "echo $0 $@"

@pytest.fixture
def repo_with_call_inspection_executable(tmp_path, dummy_test_pipeline=echo_call_program):
    """Fixture that yields a repo with an executable."""
    executable_path = tmp_path / "app"
    with open(executable_path, "w") as f:
        f.write(dummy_test_pipeline)
    os.chmod(executable_path, 0o700) # owner may read, write, or execute
    yield {'repo': tmp_path, 'executable': executable_path}


@pytest.fixture
def testpipeline_environment(repo_with_call_inspection_executable):
    """Fixture that yields a complete environment for test_pipeline.

    This comprises
     * `repo_path`   path to a git repo
     * `app_path`    path to a dummy test_pipeline app inside `repo`for introspection
     * `images_path` path to a folder with dummy images
     * `config_path` dummy path to a config file
     * `out_path`    dummy path to an output folder
    """
    repo_path = repo_with_call_inspection_executable['repo']
    app_path = repo_with_call_inspection_executable['executable']
    images_path = repo_path.parent / 'Images'
    images_path.mkdir()
    for img in ['img_01.TIF', 'img_02.TIF']:
        (images_path / img).touch()
    config_path = 'dummy/config/path'
    out_path = 'dummy/out/path'
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
def test_repo_class_can_be_constructed_from_repo_path(tmp_repo):
    helpers.Repo(tmp_repo)


def test_repo_class_cannot_be_constructed_from_non_repo_path(tmp_path):
    with pytest.raises(helpers.Repo.NotARepoException):
        helpers.Repo(tmp_path)


#-----------------------------------------------------------------------test rtp
def test_call_test_pipeline_executes_the_expected_command(testpipeline_environment):
    app_path = testpipeline_environment['app_path']
    images_path = testpipeline_environment['images_path']
    out_path = testpipeline_environment['out_path']
    config_path = testpipeline_environment['config_path']

    command_triggered = rtp.test_pipeline(app_path=app_path,
                                          out_path=out_path,
                                          config_path=config_path,
                                          images_path=images_path)

    expected_command = (f'{app_path} -f {config_path} -o {out_path} ' +
                         ' '.join(str(image_path) for image_path in images_path.glob('*')))
    assert command_triggered == expected_command