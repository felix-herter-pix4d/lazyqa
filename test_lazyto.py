import lazyto as lto
import common
from test_helpers import *

from pathlib import Path
import configparser
import re
import tempfile


def parse_lazy_test_ortho_call(call: str):
    """Extract the individual components from the call issued by lazy_test_ortho.

    Assumes that there are no white spaces in the command line arguments passed to
    test_ortho.

    >>> p = parse_lazy_test_ortho_call('./test_ortho -c "[sec]\\nkey=val" -f ./config.ini -c "[sec2]\\nkey2=val2"')

    >>> p['executable']
    './test_ortho'

    >>> p['command_line_arguments']
    '"[sec]\\nkey=val"'

    >>> p['config']
    './config.ini'

    >>> p['command_line_arguments_2']
    '"[sec2]\\nkey2=val2"'
    """
    executable_regex = r'(?P<executable>\S+)'
    command_line_arguments_regex = r'(?P<command_line_arguments>[^ ]+)'
    command_line_arguments_2_regex = r'(?P<command_line_arguments_2>[^ ]+)'
    config_regex = r'(?P<config>\S+)'
    call_regex = fr'{executable_regex}( -c {command_line_arguments_regex})? -f {config_regex}( -c {command_line_arguments_2_regex})?'
    parsed = re.match(call_regex, call)
    return {'executable': parsed.group('executable'),
            'command_line_arguments': parsed.group('command_line_arguments'),
            'config': parsed.group('config'),
            'command_line_arguments_2': parsed.group('command_line_arguments_2')}


@pytest.fixture
def environment_for_test_ortho(repo_with_executable,
                               tmp_path):
    """Fixture that yields a complete environment for test_pipeline.

    This comprises
     * `repo_path`   Path to a git repo.
     * `app_path`    Path to a dummy test_pipeline app inside `repo`for introspection.
                     The app is a dummy that returns the call with which it was invoked
                     to allow inspecting if the arguments passed to the app are correct.
     * `config_path` Path to a config file.
     * `out_path`    Path to an output folder.
    """
    repo_with_call_inspection_executable = repo_with_executable()
    repo_path = repo_with_call_inspection_executable['repo']
    app_path = repo_with_call_inspection_executable['executable']
    config_path = insert_dummy_config(repo_path.parent)
    out_path = Path(tempfile.mkdtemp(dir=tmp_path, prefix='out_'))
    return {'repo_path': repo_path,
            'app_path': app_path,
            'config_path': config_path,
            'out_path': out_path}


def test_create_lazyto_out_folder_name_is_correct_without_optional_description(environment_for_test_ortho):
    env = environment_for_test_ortho
    (env['out_path'] / '001_123456_ortho').touch()

    out_folder_name = lto.create_lazyto_out_folder_name(repo = common.Repo(env['app_path']),
                                                        out_path = env['out_path'],
                                                        description ='ortho')

    parsed = lto.parse_lazyto_out_folder_name(out_folder_name)
    assert(parsed['id'] == '002')
    assert(parsed['sha1'] is not None)
    assert(parsed['description'] == 'ortho')


def test_create_lazyto_out_folder_name_is_correct_with_optional_description(environment_for_test_ortho):
    env = environment_for_test_ortho
    (env['out_path'] / '001_123456_ortho').touch()

    out_folder_name = lto.create_lazyto_out_folder_name(repo = common.Repo(env['app_path']),
                                                        out_path = env['out_path'],
                                                        description ='ortho',
                                                        optional_description = 'this is optional') # CONTINUE HERE

    parsed = lto.parse_lazyto_out_folder_name(out_folder_name)
    assert(parsed['id'] == '002')
    assert(parsed['sha1'] is not None)
    assert(parsed['description'] == 'ortho')
    assert(parsed['optional_description'] == 'thisIsOptional')


@pytest.mark.skip(reason = "to be implemented")
def test_lazy_test_pipeline_writes_log_to_qa_test_case_folder(make_environment_for_test_pipeline):
    pass # TODO: implement


def test_calling_test_ortho_calls_the_expected_command(tmp_path, repo_with_executable):
    app_path = repo_with_executable(executable=echo_call_program)['executable']
    command_line_arguments = r'[section]\nkey=value'
    command_line_arguments_2 = r'[section2]\nkey2=value2'
    out_path = tmp_path
    config_path = '/path/to/config.ini'

    command = lto.test_ortho(
               app_path = app_path,
               out_path = out_path,
               config_path = config_path,
               command_line_arguments = command_line_arguments,
               command_line_arguments_2 = command_line_arguments_2,
               live_output = False)

    sanitize = lambda s: s.replace('\\n', '\n')
    expected_command = f'{app_path} -c {sanitize(command_line_arguments)} -f {config_path} -c {sanitize(command_line_arguments_2)}'
    assert command == expected_command


def assert_that_command_creates_folder(command, parent: Path, folder_pattern: str):
    """Check that the command creates a folder matching the folder pattern inside the parent folder path."""
    pre_matches = list(parent.glob(folder_pattern))
    command()
    post_matches = list(parent.glob(folder_pattern))
    assert(len(pre_matches) == 0)
    assert(len(post_matches) == 1)


def test_lazy_test_ortho_creates_correct_output_folder(environment_for_test_ortho):
    env = environment_for_test_ortho
    command = lambda: lto.lazy_test_ortho(app_path = env['app_path'],
                                          out_root_path = env['out_path'],
                                          config_path = env['config_path'],
                                          live_output = False)
    assert_that_command_creates_folder(command,
                                       parent = env['out_path'],
                                       folder_pattern = '001_*_ortho')


def test_lazy_test_ortho_creates_correct_debug_folder(environment_for_test_ortho):
    env = environment_for_test_ortho
    command = lambda: lto.lazy_test_ortho(app_path = env['app_path'],
                                          out_root_path = env['out_path'],
                                          config_path = env['config_path'],
                                          generate_debug_output = True,
                                          live_output = False)
    assert_that_command_creates_folder(command,
                                       parent = env['out_path'],
                                       folder_pattern = '001_*_ortho/debug')


def test_lazy_test_ortho_copies_config(environment_for_test_ortho):
    env = environment_for_test_ortho
    get_all_config_copies = lambda : list(env['out_path'].glob('*/{lto.copied_config_name}'))
    assert len(get_all_config_copies()) == 0

    lto.lazy_test_ortho(app_path = env['app_path'],
                        out_root_path = env['out_path'],
                        config_path = env['config_path'],
                        live_output = False)

    config_copies = list(env['out_path'].glob(f'*/{lto.enriched_config_name}'))
    assert len(config_copies) == 1
    assert content_of(env['config_path']) in content_of(config_copies[0]) # not equal, copy is enriched


def test_enriched_config_has_correct_out_path():
    out_path = Path('/path/to/output/001_123456_ortho_myExperiment/')

    enriched = lto.enrich_config(config='', out_path=out_path)

    assert(common.parse_config( enriched )['output']['filename'] == str(out_path / f'{out_path.name}.tif'))


def test_enriched_config_has_correct_debug_path():
    debug_out_path = Path('/path/to/debug')

    enriched = lto.enrich_config(config = '', out_path = Path(), debug_output_path = debug_out_path)

    assert(common.parse_config( enriched )['color_balance']['debug_tiles_path'] == str(debug_out_path))


def test_enriched_config_has_correct_options_for_input_from_test_pipeline():
    test_pipeline_project_path = Path('/path/to/Output/001_123456_snowyMountain_myExperiment/')

    enriched = lto.enrich_config(config = '', out_path = Path(), test_pipeline_project_path = test_pipeline_project_path)

    parsed = common.parse_config( enriched )
    assert(parsed['images']['opfProject'] == str(test_pipeline_project_path / 'opf' / 'project.json'))
    assert(parsed['dsm']['input_file'] == str(test_pipeline_project_path / 'dsm.tiff'))


def test_lazy_test_ortho_uses_default_config_location_when_not_specified(environment_for_test_ortho):
    env = environment_for_test_ortho

    command_called = lto.lazy_test_ortho(app_path = env['app_path'],
                                         out_root_path = env['out_path'],
                                         config_path = env['config_path'],
                                         live_output = False)
    parsed = parse_lazy_test_ortho_call(command_called)
    assert(config_subset(content_of(env['config_path']), content_of(parsed['config'])))


def test_lazy_test_ortho_uses_specified_config_location(environment_for_test_ortho):
    env = environment_for_test_ortho
    specified_config = env['config_path'].parent / 'another_config.ini'
    write_file('[a_different_section]\nnew_key=ney_val\n', specified_config)

    command_called = lto.lazy_test_ortho(app_path = env['app_path'],
                                         out_root_path = env['out_path'],
                                         config_path = specified_config,
                                         live_output = False)

    parsed = parse_lazy_test_ortho_call(command_called)
    assert(config_subset(content_of(specified_config), content_of(parsed['config'])))


if __name__ == "__main__":

    import doctest
    doctest.testmod()