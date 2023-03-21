import lazytp as ltp
import common
from test_helpers import *

import re

def test_calling_test_pipeline_calls_the_expected_command(make_environment_for_test_pipeline):
    env = make_environment_for_test_pipeline(executable = echo_call_program)
    command_triggered = ltp.test_pipeline(app_path = env['app_path'],
                                          out_path = env['out_path'],
                                          config_path = env['config_path'])

    expected_command = f"{env['app_path']} -f {env['config_path']} -o {env['out_path']}"
                         #' '.join(str(image_path) for image_path in env['images_path'].glob('*')))
    assert command_triggered == expected_command


def test_lazy_test_pipeline_copies_config(make_environment_for_test_pipeline):
    env = make_environment_for_test_pipeline()
    get_all_config_copies = lambda : list(env['out_path'].glob('*/config.ini'))
    assert len(get_all_config_copies()) == 0

    ltp.lazy_test_pipeline(app_path = env['app_path'],
                           out_root_path = env['out_path'],
                           config_path = env['config_path'],
                           images_path = env['images_path'])

    config_copies = list(env['out_path'].glob('*/config.ini'))
    assert len(config_copies) == 1
    assert content_of(env['config_path']) in content_of(config_copies[0]) # not equal, copy is enriched


def test_lazy_test_pipeline_reads_local_config(make_environment_for_test_pipeline):
    env = make_environment_for_test_pipeline(executable=echo_call_program)
    os.chdir(env['config_path'].parent)

    # when no config path is specified...
    what_was_called = ltp.lazy_test_pipeline(app_path = env['app_path'],
                                             out_root_path = env['out_path'],
                                             images_path = env['images_path'])

    # ...the local config (at env['config_path']) is used
    get_config_argument = lambda call : re.match(r'.*-f (\S*).*', call).group(1) # capture argument after '-f' flag
    config_used_path = get_config_argument(what_was_called)
    assert content_of(env['config_path']) in content_of(config_used_path) # not equal, copy is enriched


def test_lazy_test_pipeline_creates_correct_output_folder_when_no_description_is_given(make_environment_for_test_pipeline):
    env = make_environment_for_test_pipeline()

    ltp.lazy_test_pipeline(app_path = env['app_path'],
                           out_root_path = env['out_path'],
                           images_path = env['images_path'],
                           config_path = env['config_path'])

    expected_qa_project_name = common.camel_case(env['images_path'].parent.name)
    expected_id = '004' # previous highest id was 003
    all_correct_output_folders = env['out_path'].glob(f"{expected_id}*{expected_qa_project_name}")
    assert len(list(all_correct_output_folders)) == 1


def test_lazy_test_pipeline_creates_correct_output_folder_when_description_is_given(make_environment_for_test_pipeline):
    env = make_environment_for_test_pipeline()
    description = "this is a test case"

    ltp.lazy_test_pipeline(app_path = env['app_path'],
                           out_root_path = env['out_path'],
                           optional_description = description,
                           images_path = env['images_path'],
                           config_path = env['config_path'])

    expected_qa_project_name = common.camel_case(env['images_path'].parent.name)
    expected_description = common.camel_case(description)
    expected_id = '004' # previous highest id was 003
    all_correct_output_folders = env['out_path'].glob(
        f"{expected_id}*{expected_qa_project_name}*{expected_description}")
    assert len(list(all_correct_output_folders)) == 1


def test_lazy_test_pipeline_writes_log_to_qa_test_case_folder(make_environment_for_test_pipeline):
    env = make_environment_for_test_pipeline()
    collect_current_qa_test_cases = lambda : set(env['out_path'].glob('*'))
    previous_qa_test_cases = collect_current_qa_test_cases()

    ltp.lazy_test_pipeline(app_path = env['app_path'],
                           out_root_path = env['out_path'],
                           images_path = env['images_path'],
                           config_path = env['config_path'])

    new_qa_test_case_path = next(iter(collect_current_qa_test_cases() - previous_qa_test_cases))
    assert 'log.txt' in {content.name for content in new_qa_test_case_path.glob('*')}


def test_stitched_result_name_contains_id_and_description():
    result_name = ltp.derive_stitched_result_name('015_1234567890_snowyHillside_increasedStepSizeTo42')
    assert result_name == '015_snowyHillside_increasedStepSizeTo42_stitched.tiff'