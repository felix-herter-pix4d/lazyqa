import batchltp as btp
import common
from test_helpers import *

import pytest
import re


@pytest.fixture
def two_qa_projects_with_images(tmp_path):
    """Fixture that yields two QA projects, each with subdirectory 'images' containing dummy images."""
    project_names = ('snowy_hillside', 'rolling_mountain')
    qa_project_paths = tuple(tmp_path / project_name for project_name in project_names)
    images_paths = tuple(qa_project_path / 'images' for qa_project_path in qa_project_paths)
    for images_path in images_paths:
        images_path.mkdir(parents=True, exist_ok=True)
        insert_dummy_images(images_path)
    yield {'qa_project_path_1': qa_project_paths[0], 'images_path_1': images_paths[0],
           'qa_project_path_2': qa_project_paths[1], 'images_path_2': images_paths[1]}


def parse_lazytp_call(call: str):
    #executable_regex = config_path_regex = out_path_regex = r'(\S+)' # TODO: use this
    call_regex = r'(\S+) -f (\S+) -o (\S+)' # captures 1. executable name, 2. config path, 3. out path
    parsed = re.match(call_regex, call)
    return {'executable': parsed.group(1), 'config': parsed.group(2), 'output': parsed.group(3)}


def test_guess_images_subfolder_returns_subfolder_named_images_when_present(tmp_path):
    images_folder = tmp_path / 'images'
    images_folder.mkdir()

    assert btp.guess_images_subfolder(tmp_path) == images_folder


def test_guess_images_subfolder_returns_first_sole_subfolder_with_images(tmp_path):
    images_folder = tmp_path / 'the_input'
    images_folder.mkdir()
    insert_dummy_images(images_folder)
    (tmp_path / 'no_input').mkdir()

    assert btp.guess_images_subfolder(tmp_path) == images_folder


def test_guess_images_subfolder_raises_exception_when_images_subfolder_ambiguous(tmp_path):
    candidates_paths = (tmp_path / 'images1', tmp_path / 'images2')
    for candidates_path in candidates_paths:
        candidates_path.mkdir()
        insert_dummy_images(candidates_path)
    with pytest.raises(btp.AmbiguousQAProjectLayoutException):
        btp.guess_images_subfolder(tmp_path)


def test_gather_input_paths_from_qa_projects_root_collects_all_valid_paths(two_qa_projects_with_images):
    qa_projects_root_path = two_qa_projects_with_images['qa_project_path_1'].parent

    images_paths = btp.gather_input_paths_from_qa_projects_root(qa_projects_root_path)['images_paths']

    expected_images_paths = [two_qa_projects_with_images['images_path_1'], two_qa_projects_with_images['images_path_2']]
    assert images_paths == expected_images_paths


def test_gather_input_paths_from_qa_projects_root_collects_all_ambiguous_paths(tmp_path):
    ambiguous_project = tmp_path / 'ambiguous'
    for images_path in (ambiguous_project/'inputs_1', ambiguous_project/'inputs_2'):
        images_path.mkdir(parents = True)
        insert_dummy_images(images_path)

    ambiguous_qa_projects = btp.gather_input_paths_from_qa_projects_root(ambiguous_project.parent)['ambiguous_qa_projects']

    expected_ambiguous_projects = [ambiguous_project]
    assert ambiguous_qa_projects == expected_ambiguous_projects


# Reasonability checks to build trust that the call to batchltp behaves correctly

def make_lazytp_args(env: dict,
                     app_path: Path = None,
                     out_root_path: Path = None,
                     images_path: Path = None,
                     optional_description: str = None,
                     config_path: Path = None):
    """Return a parameter-bundle that can be passed to lazytp, and thus, to batch_ltp."""
    return {"app_path": app_path or env["app_path"],
            "out_root_path": out_root_path or env["out_path"],
            "images_path": images_path or env['images_path'],
            "optional_description": optional_description or "some description",
            "config_path": config_path or env["config_path"]}

def test_calling_batchltp_with_one_project_inserts_correct_images_path_into_config(environment_for_test_pipeline):
    env = environment_for_test_pipeline
    images_path = Path("path/to/images")
    projects = [make_lazytp_args(env, images_path = images_path)]

    command_triggered = next(btp.batch_ltp(projects))

    path_to_used_config = parse_lazytp_call(command_triggered)['config']
    assert f'path = {images_path}' in content_of(path_to_used_config)

def test_calling_batchltp_with_two_projects_inserts_correct_images_path_into_configs(environment_for_test_pipeline):
    env = environment_for_test_pipeline
    images_paths = (Path("first/path/to/images"),
                    Path("second/path/to/images"))
    projects = (make_lazytp_args(env, images_path = images_path) for images_path in images_paths)

    commands_triggered = list(btp.batch_ltp(projects))

    assert len(commands_triggered) == 2
    paths_to_used_configs = [parse_lazytp_call(command_triggered)['config']
                             for command_triggered in commands_triggered]
    assert f'path = {images_paths[0]}' in content_of(paths_to_used_configs[0])
    assert f'path = {images_paths[1]}' in content_of(paths_to_used_configs[1])

def test_calling_batchltp_with_one_project_creates_correct_output_folder(environment_for_test_pipeline):
    env = environment_for_test_pipeline
    projects = [make_lazytp_args(env)]

    command_triggered = next(btp.batch_ltp(projects))

    path_to_output = Path(parse_lazytp_call(command_triggered)['output'])
    assert path_to_output.exists()
    assert common.is_test_case_name(path_to_output.name)