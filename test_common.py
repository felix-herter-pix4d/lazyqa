import common
import lazytp as ltp
from test_helpers import *

import pytest
import subprocess
from pathlib import Path

def subprocess_output(command: list[str]):
    """Return stdout of the command."""
    result = subprocess.run(command, capture_output=True)
    result.check_returncode()
    return result.stdout.decode('utf-8').strip()


@pytest.fixture
def repo_with_dev_branch(repo_dir, repo_with_executable):
    git('checkout', '-b', 'dev_branch', repo=repo_dir)
    repo_dir = repo_with_executable(repo_dir)['repo'] # adds a commit to repo 'repo_dir'
    return repo_dir


#--------------------------------------------------------------test misc helpers
def test_camel_case_removes_all_forbidden_symbols():
    non_camel_case_string = "one_two.three_four five six-seven.height-nine"
    camel_case_string = "oneTwoThreeFourFiveSixSevenHeightNine"
    assert common.camel_case(non_camel_case_string) == camel_case_string


def test_that_path_into_git_repo_is_correctly_detected(repo_with_executable):
    assert common.is_part_of_git_repo(repo_with_executable()['executable'])

def test_execute_command_copies_stdout_to_out_path(tmpdir):
    content = 'hello world!'
    command = [f'echo "{content}"']
    out_file = tmpdir / "output.txt"

    common.execute_command(command, out_file=out_file)

    stored_content = content_of(out_file)
    assert stored_content  == content


#----------------------------------------------------------------------test Repo
def test_repo_class_can_be_constructed_from_repo_path(repo_dir):
    common.Repo(repo_dir)


def test_repo_class_cannot_be_constructed_from_non_repo_path(tmp_path):
    with pytest.raises(common.Repo.NotARepoException):
        common.Repo(tmp_path)


def test_repo_class_retrieves_patch(repo_with_dev_branch):
    repo = common.Repo(repo_with_dev_branch)
    patch = repo.get_patch(_from=repo.get_merge_base('HEAD', repo.guess_main_branch()))
    file_mode = '100644' if os.name == 'nt' else '100755' # file modes differ on differen OS
    expected_content = ('---\n'
                        ' app | 1 +\n'
                        ' 1 file changed, 1 insertion(+)\n'
                        f' create mode {file_mode} app\n\n'
                        'diff --git a/app b/app\n'
                        f'new file mode {file_mode}\n'
                        'index 0000000..827a748\n'
                        '--- /dev/null\n'
                        '+++ b/app\n'
                        '@@ -0,0 +1 @@\n'
                        '+echo $0 $@\n'
                        '\\ No newline at end of file\n')
    assert expected_content in patch


def test_repo_class_untracked_changes_returns_correct_patch_when_there_are_changes(repo_with_executable):
    repo_and_executable = repo_with_executable()
    with open(repo_and_executable['executable'], 'a') as file:
        file.write("untracked content")
    repo = common.Repo(repo_and_executable['repo'])

    patch = repo.get_untracked_changes()

    expected_content = ('--- a/app\n'
                        '+++ b/app\n'
                        '@@ -1 +1 @@\n'
                        '-echo $0 $@\n'
                        '\\ No newline at end of file\n'
                        '+echo $0 $@untracked content\n'
                        '\\ No newline at end of file')
    assert expected_content in patch


def test_repo_class_untracked_changes_returns_empty_patch_when_there_are_no_changes(repo_dir):
    repo = common.Repo(repo_dir)
    patch = repo.get_untracked_changes()
    assert patch == ''


#----------------------------------------------------------test specific helpers
def test_get_next_id_returns_the_correct_id(out_dir_with_test_case_results):
    assert common.get_next_id(out_dir_with_test_case_results) == '004' # highest existing id is '003'


def test_that_test_case_names_are_correct_when_no_description_given():
    sha1 = '1234567890'
    _id = '001'
    project_name = 'snowy_Hillside'
    test_case_name = common.create_test_case_name(_id, sha1, project_name)
    assert test_case_name == '001_1234567890_snowyHillside'


def test_that_test_case_names_are_correct_when_description_given():
    sha1 = '1234567890'
    _id = '001'
    project_name = 'snowy_Hillside'
    description = "increasedStepSizeTo42"
    test_case_name = common.create_test_case_name(_id, sha1, project_name, description)
    assert test_case_name == '001_1234567890_snowyHillside_increasedStepSizeTo42'


def test_create_input_block_for_config_returns_correct_block(make_environment_for_test_pipeline):
    env = make_environment_for_test_pipeline()

    config_block = ltp.create_input_block_for_config(images_path=env['images_path'])

    image_names = ','.join(image_path.name for image_path in env['images_path'].glob('*'))
    expected = ('[metric]\n'
                f"path = {env['images_path']}\n"
                f'inputs = {image_names}\n')
    assert config_block == expected