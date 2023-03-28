import lazyto as lto
import common
from test_helpers import *

from pathlib import Path
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
     * `out_path`    Path to an output folder.
    """
    repo_with_call_inspection_executable = repo_with_executable()
    repo_path = repo_with_call_inspection_executable['repo']
    app_path = repo_with_call_inspection_executable['executable']
    out_path = Path(tempfile.mkdtemp(dir=tmp_path, prefix='out_'))
    return {'repo_path': repo_path,
            'app_path': app_path,
            'out_path': out_path}


def test_calling_test_ortho_calls_the_expected_command(repo_with_executable):
    app_path = repo_with_executable(executable=echo_call_program)['executable']
    command_line_arguments = r'[section]\nkey=value'
    command_line_arguments_2 = r'[section2]\nkey2=value2'
    config_path = '/path/to/config.ini'

    command = lto.test_ortho(
               app_path = app_path,
               config_path = config_path,
               command_line_arguments = command_line_arguments,
               command_line_arguments_2 = command_line_arguments_2,
               live_output = False)

    sanitize = lambda s: s.replace('\\n', '\n')
    expected_command = f'{app_path} -c {sanitize(command_line_arguments)} -f {config_path} -c {sanitize(command_line_arguments_2)}'
    assert command == expected_command


def test_lazy_test_ortho_creates_correct_output_folder(environment_for_test_ortho):
    env = environment_for_test_ortho
    pre_matches = list(env['out_path'].glob('001_*_ortho'))

    lto.lazy_test_ortho(app_path = env['app_path'], out_root_path = env['out_path'])

    post_matches = list(env['out_path'].glob('001_*_ortho'))
    assert(len(pre_matches) == 0)
    assert(len(post_matches) == 1)


if __name__ == "__main__":
    parse_lazy_test_ortho_call(r'/path/test_ortho -c "[section]\nkey=value\n" -f ./config.ini -c "[section2]\nkey=value"')
    parse_lazy_test_ortho_call(r'/path/test_ortho -c "[section]\nkey=value\n" -f ./config.ini')
    parse_lazy_test_ortho_call(r'/path/test_ortho -f ./config.ini')

    import doctest
    doctest.testmod()