import batchltp as btp
import common
from test_helpers import *

import pytest
import re


def parse_lazytp_call(call: str):
    #executable_regex = config_path_regex = out_path_regex = r'(\S+)' # TODO: use this
    call_regex = r'(\S+) -f (\S+) -o (\S+)' # captures 1. executable name, 2. config path, 3. out path
    parsed = re.match(call_regex, call)
    return {'executable': parsed.group(1), 'config': parsed.group(2), 'output': parsed.group(3)}


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

