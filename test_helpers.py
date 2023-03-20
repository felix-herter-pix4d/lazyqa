from pathlib import Path

def content_of(file: Path) -> str:
    """Return the content of the file."""
    result = None
    with open(file) as f:
        result = f.read().strip()
    return result


    try:
        result.check_returncode()
    except subprocess.CalledProcessError as err:
        print(f"subprocess: '{command}' raised {err}\nstdout: {result.stderr.decode('utf-8').strip()}")
        raise err
echo_call_program = "echo $0 $@"


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


    config_path = path / 'config.ini'
     * `repo_path`   Path to a git repo.
     * `app_path`    Path to a dummy test_pipeline app inside `repo`for introspection.
                     The app is a dummy that returns the call with which it was invoked
                     to allow inspecting if the arguments passed to the app are correct.
     * `images_path` Path to a folder with dummy images.
     * `config_path` Dummy path to a config file.
     * `out_path`    Dummy path to an output folder.