#!/usr/bin/python3

import common

import argparse
import configparser
import sys
from pathlib import Path


enriched_config_name = 'ortho.ini' # we copy the user's config to the output folder


def create_lazyto_out_folder_name(repo: common.Repo,
                                  out_path: Path,
                                  description: str,
                                  optional_description: str = None,
                                  reuse_id: bool = False):
    """Generate a name for the output of test_ortho comprising id, sha1, and description.

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
               out_path: Path,
               config_path: Path,
               command_line_arguments: str = None,
               command_line_arguments_2: str = None,
               live_output=True):
    """Execute test_ortho in a subprocess.

    app_path:                  Path to the test_ortho executable.
    out_path:                  Path to where the results should be stored.
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

    return common.execute_command(command, out_file=out_path/"log.txt", live_output=live_output)


def add_to_config(parser: configparser.ConfigParser, section: str, key: str, value: str):
    """Add key/value pair to the given section of the config parser.

    If the section does not exists, create it.
    """
    if section not in parser.sections():
        parser[section] = {}
    parser[section][key] = value


def enrich_config(config: str,
                  out_path: Path,
                  debug_output_path: Path = None,
                  test_pipeline_project_path: Path = None):
    """Add/alter fields in the config.

    Change the config to make sure that the result ortho is at the right
    location. Additionally enable running from test_pipeline results or writing
    of debug information.

    config:            Original config string.
    out_path:          This path will be set at the output folder for the
                       resulting ortho.
    debug_output_path: If not None, this path will be used as destination for
                       the debug tiles.
    test_pipeline_project_path: It not None, this path is assumed to point to
                                an output folder of lazy_test_pipeline. The
                                config will be altered to read the dsm and
                                project opf description from this folder.
    """
    parser = common.parse_config(config)

    # add the new output filename to the config section 'output'
    ortho_path = out_path / f'{out_path.name}.tif'
    add_to_config(parser, section='output', key='filename', value=str(ortho_path))

    # add debug output path
    if debug_output_path is not None:
        add_to_config(parser, section='color_balance', key='debug_tiles_path', value=str(debug_output_path))

    # add information to run from lazy_test_pipeline output
    if test_pipeline_project_path is not None:
        add_to_config(parser, section='images', key='opfProject', value=str(test_pipeline_project_path / 'opf' / 'project.json'))
        add_to_config(parser, section='dsm', key='input_file', value=str(test_pipeline_project_path / 'dsm.tiff'))

    # enriched config to string
    lines = []
    for section in parser.sections():
        lines.append(f'[{section}]\n')
        for k, v in parser[section].items():
            lines.append(f'{k} = {v}\n')
        lines.append('\n')
    if lines:
        del lines[-1] # remove spurious last newline
    enriched_config = ''.join(lines)

    return enriched_config


def create_enriched_config(config_path: Path,
                           out_path: Path,
                           debug_output_path: Path,
                           test_pipeline_project_path: Path):
    """Copy config to out_path, add/overwrite some fields.

    If config_path is None, default to the file named 'config.ini' at the local
    directory.
    Dictates the correct out path and filename of the ortho.

    Returns the path to the copied config.
    """
    if not config_path.exists():
        print(f'Config expected at {config_path.absolute()} but not found.')
        sys.exit(-1)

    copied_config_path = out_path / enriched_config_name
    common.write_file(content = enrich_config(config = common.content_of(config_path),
                                              out_path=out_path,
                                              debug_output_path=debug_output_path,
                                              test_pipeline_project_path=test_pipeline_project_path),
                      file_path = copied_config_path)

    return copied_config_path


def lazy_test_ortho(app_path: Path,
                    out_root_path: Path,
                    config_path: Path,
                    description: str = 'ortho',
                    optional_description: str = None,
                    generate_debug_output: bool = False,
                    test_pipeline_project_path: Path = None,
                    live_output: bool = True):
    """Run test_ortho and put results in a new folder.

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

    app_path:              Path to the test_ortho executable. It is assumed that it lives
                           somewhere in the fastmap repo.
    out_root_path:         Path to a folder. The output folder will be created as a
                           subfolder of this.
    config_path:           Path to the config file.
    description:           Identifier string that will part of the output folder name.
                           Could be the dataset/project name.
    optional_description:  Additional string to be added to the output folder name.
    generate_debug_output: If true, create debug subfolder and trigger
                           generation of debug tiles.
    test_pipeline_project_path: Path to output folder of lazy_test_pipeline. If specified,
                                 use that output as input for test_ortho.
    live_output:           If true, prints the output of the test_ortho execution.
    """
    repo = common.Repo(app_path)

    out_path = out_root_path / create_lazyto_out_folder_name(repo=repo,
                                                             out_path=out_root_path,
                                                             description=description,
                                                             optional_description=optional_description)
    out_path.mkdir()

    debug_output_path = None
    if generate_debug_output:
        debug_output_path = out_path / 'debug'
        debug_output_path.mkdir()

    copied_config_path = create_enriched_config(config_path = config_path,
                                                out_path = out_path,
                                                debug_output_path = debug_output_path,
                                                test_pipeline_project_path = test_pipeline_project_path)

    common.add_patch_not_on_main_branch(repo=repo, out_path=out_path)
    common.add_patch_dirty_state(repo=repo, out_path=out_path)

    output = test_ortho(app_path = app_path,
                        out_path=out_path,
                        config_path = copied_config_path,
                        live_output = live_output)

    return output # for testing purposes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description =
           """
           lazy_to, test_ortho for lazy people.

           This script calls test_ortho, checks for a stale binary, writes
           the results to an automatically generated output folder that tracks
           version information.
           """,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-x', '--test-ortho',
        required=True,
        help='Path to test_ortho executable. Assumed to be somewhere inside the rag repo.'
    )

    parser.add_argument(
        '-o', '--out-path',
        default = '.',
        help='Path to where the output should be stored. The script will add a new sub-directory.'
    )

    parser.add_argument(
        '-c', '--config',
        default = './config.ini',
        help='Path to the config.ini. Default is ./config.ini. Will be copied and expanded (see output folder).'
    )

    parser.add_argument(
        '-p', '--project-name',
        default = 'ortho',
        help="Name to identify the project, to 'ortho'."
    )

    parser.add_argument(
        '-d', '--description',
        help='Optional description. It will be appended to the output folder name.'
    )

    parser.add_argument(
        '-t', '--test-pipeline-output',
        help='Optional, path to output folder of lazy_test_pipeline to process using that opf.'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help="Optional, generate debug tiles in subfolder 'debug'.")

    parser.add_argument(
        '--no-confirmation',
        action='store_true',
        help='Optional, suppress any user prompts. Handy when called in non-interactive script.'
        )

    args = vars(parser.parse_args())

    common.check_executable(Path(args['test_ortho']),
                            recompile = False if os.name == 'nt' else True, # have to figure out how to build using cmake on Windows
                            prompt_user_confirmation = not args['no_confirmation'])

    lazy_test_ortho(app_path = Path(args['test_ortho']),
                    out_root_path = Path(args['out_path']),
                    config_path = Path(args['config']),
                    description = args['project_name'],
                    optional_description = args['description'],
                    generate_debug_output = args['debug'],
                    test_pipeline_project_path = Path(args['test_pipeline_output']),
                    )
