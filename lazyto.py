#!/usr/bin/python3

import common

import re
from pathlib import Path


def create_lazyto_out_folder_name(repo: common.Repo,
                                  out_path: Path,
                                  description: str,
                                  optional_description: str = None,
                                  reuse_id: bool = False):
    """Generate a name for the output of test_pipeline comprising id, sha1, and description.

    Per default, the id is more than the largest id used in out_path.
    It can be specified to re-use the largest id that is present, for use cases where different
    runs should be identifiable as belonging to the same batch.
    ATTENTION: When re-using the last id, make sure that the description is unique. To make this
    easier, the description is taken, as is, and not converted to camel case in this function.
    """
    _id = common.find_highest_id(out_path) if reuse_id else common.get_next_id(out_path)
    sha1 = repo.get_sha_of_branch('HEAD', short=True)
    components = [_id, sha1, description]
    if optional_description is not None:
        components.append(common.camel_case(optional_description))
    return common.SEPARATOR.join(components)


def parse_lazyto_out_folder_name(name: str):
    """Extract the individual components from the lazy_test_ortho out folder name.

    >>> p = parse_lazyto_out_folder_name('001_123456_ortho_userDescription')

    >>> p['id']
    '001'
    >>> p['sha1']
    '123456'
    >>> p['description']
    'ortho'
    >>> p['optional_description']
    'userDescription'
    """
    parsed = common.parse_test_case_name(name)
    parsed['description'] = parsed['dataset_name'] # in context of this module, we call it description
    del parsed['dataset_name']
    return parsed


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

    app_path:      Path to the test_ortho executable. It is assumed that it lives
                   somewhere in the fastmap repo.
    out_root_path: Path to a folder. The output folder will be created as a
                   subfolder of this.
    config_path:   Path to the config file. Default to './config.ini'
    description:   Identifier string that will part of the output folder name.
                   Could be the dataset/project name.

    """
    repo = common.Repo(app_path)

    out_path = out_root_path / create_lazyto_out_folder_name(repo=repo,
                                                             out_path=out_root_path,
                                                             description=description)
    out_path.mkdir()


if __name__ == '__main__':

    import doctest
    doctest.testmod()

    #args = ['~/Code/pix4d-rag/build-fastmap-Release/bin/test_ortho -c "[general]\\nroot=/home/fherter/Tickets/cv11_stripe_artifacts_GPU_fast/Data/museumOblique" -f /home/fherter/Tickets/cv11_stripe_artifacts_GPU_fast/Data/museumOblique/inputs.conf']
    #common.execute_command(args, live_output=True)