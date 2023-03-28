#!/usr/bin/python3

import common
from pathlib import Path


def ensure_double_quotes(s: str):
    """Make sure that s is surrounded by double quotes"""
    if s is None:
        return s
    return f'"{s}"' if s[0] != '"' else s


def test_ortho(app_path: Path,
               config_path: Path,
               command_line_arguments: str = None,
               command_line_arguments_2: str = None,
               live_output=True):
    """Execute test_ortho in a subprocess.

    app_path:                  Path path to the test_ortho executable.
    config_path:               Path to the config.ini
    command_line_arguments:    String containing command line arguments passed before the config.
    command_line_arguments_ 2: String containing command line arguments passed after the config.
                               This can be useful to enforce a configuration by overwriting any
                               values passed via the config.ini.
    live_output:               If true, print stdout of test_ortho.
    """
    def append_command_line_argument(command, arguments):
        return command if arguments is None else command + ' -c ' + ensure_double_quotes(arguments)

    command = str(app_path)
    command = append_command_line_argument(command, command_line_arguments)
    command += ' -f ' + str(config_path)
    command = append_command_line_argument(command, command_line_arguments_2)

    return common.execute_command(command, live_output=live_output)


def lazy_test_ortho(app_path: Path,
                    out_root_path: Path,
                    description: str = 'ortho'):
    """Create a folder for the output of test_ortho.

    The output folder will be a subfolder of `out_root_path` and will be named
    following the pattern,

        <id>_<sha1>_<description>_<optionalDescription>
    e.g.
        003_1234567890_ortho_increasedStepSizeTo42

    <id> is an index that is per default one larger then the largest <id> used
         in `out_root_path`.
    <sha1> is a short sha1 of the `test_ortho` repo at the time `test_ortho`
           was called
    <description> is a mandatory description that defaults to 'ortho' but could also
                  be the name of the project
    <optionalDescription> is the `optionalDescription` sanitized into CamelCase.
    """
    repo = common.Repo(app_path)

    out_path = out_root_path
    reuse_id = False

    _id = common.find_highest_id(out_path) if reuse_id else common.get_next_id(out_path)
    sha1 = repo.get_sha_of_branch('HEAD', short=True)
    description = 'ortho'
    out_folder_name = common.SEPARATOR.join((_id, sha1, description))

    out_path = out_root_path / out_folder_name
    out_path.mkdir()


if __name__ == '__main__':

    app_path = '~/Code/pix4d-rag/build-fastmap-Release/bin/test_ortho'
    command_line_arguments = '[general]\\nroot=/home/fherter/Tickets/cv11_stripe_artifacts_GPU_fast/Data/museumOblique'
    config_path = '/home/fherter/Tickets/cv11_stripe_artifacts_GPU_fast/Data/museumOblique/inputs.conf'
    print("about to call test_ortho...")
    test_ortho(app_path=app_path,
               config_path=config_path,
               command_line_arguments=command_line_arguments,
               live_output=True)


    #args = ['~/Code/pix4d-rag/build-fastmap-Release/bin/test_ortho -c "[general]\\nroot=/home/fherter/Tickets/cv11_stripe_artifacts_GPU_fast/Data/museumOblique" -f /home/fherter/Tickets/cv11_stripe_artifacts_GPU_fast/Data/museumOblique/inputs.conf']
    #common.execute_command(args, live_output=True)