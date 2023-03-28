#!/usr/bin/python3

import common

import argparse
import datetime
import os
import shutil
import subprocess
import time
import sys
from pathlib import Path


enriched_config_name = 'pipeline.ini' # we copy the user's config to the output folder
                                      # and enrich it with additional configurations


def test_pipeline(app_path: Path,
                  out_path: Path,
                  config_path: Path,
                  live_output=True):
    command = str(app_path)
    command += ' -f ' + str(config_path)
    command += ' -o ' + str(out_path)
    return common.execute_command(command, out_file=out_path/"log.txt", live_output=live_output)


def create_input_block_for_config(images_path: Path = None):
    """Return a block for the config.ini that contains all input images."""
    image_names = ','.join(image_path.name for image_path in images_path.glob('*'))
    return ('[metric]\n'
            f'path = {images_path}\n'
            f'inputs = {image_names}\n')


def derive_stitched_result_name(test_case_name: str):
    """Derived name has the form '<id>_<optionalDescription>_stitched.tiff'.'"""
    parsed = common.parse_test_case_name(test_case_name)
    components = [parsed['id'], parsed['dataset_name']]
    if parsed['optional_description'] is not None:
        components += [parsed['optional_description']]
    components += ['stitched.tiff']
    return '_'.join(components)


def rename_stitched_tiff(out_subfolder_path: str):
    """Add test case id and user description to the too generic name 'stitched.tiff'."""
    stitched_tiff_path = out_subfolder_path / 'stitched.tiff'
    test_case_name = out_subfolder_path.name
    if stitched_tiff_path.exists():
        stitched_tiff_path.rename(out_subfolder_path / derive_stitched_result_name(test_case_name))


class colors:
    red = '\033[91m'
    orange = '\033[93m'
    normal = '\033[0m'

def check_executable(app_path: str, prompt_user_confirmation:bool = True):
    # wrong path to binary?
    if not app_path.exists():
        print(f'{colors.red}',
              f'binary {app_path} not found',
              f'{colors.normal}')
        exit(-1)

    # binary actually a directory?
    if app_path.is_dir():
        print(f'{colors.red}',
              f'binary {app_path} is actually a directory',
              f'{colors.normal}')
        exit(-1)

    # binary not executable?
    if not os.access(app_path, os.X_OK):
        print(f'{colors.red}',
              f'binary {app_path} is not executable',
              f'{colors.normal}')
        exit(-1)

    # binary not part of git repo?
    if not common.is_part_of_git_repo(app_path):
        print(f'{colors.red}',
              f'binary {app_path} must be inside the repo',
              f'{colors.normal}')
        exit(-1)

    # stale binary?
    if prompt_user_confirmation:
        seconds_since_last_modification =  int(time.time() - os.path.getmtime(app_path))
        if seconds_since_last_modification > 60:
            print(f'{colors.orange}age:',
                  f'{datetime.timedelta(seconds=seconds_since_last_modification)}',
                  f'{colors.normal}')
            input('(press any key to continue)')


def get_lazytp_test_case_name(repo: common.Repo,
                              out_path: Path,
                              images_path: Path,
                              optional_description: str = None,
                              reuse_id = False):
    """Generate a name for the test case comprising id, sha1, project name, and (optionally) a description.

    Per default, the id is more than the largest qa test case id we find in the out_path.
    It can be specified to re-use the largest id that is present, for use cases where different
    qa test cases should be identifiable as belonging to one batch.
    """
    _id = common.find_highest_id(out_path) if reuse_id else common.get_next_id(out_path)
    sha1 = repo.get_sha_of_branch('HEAD', short=True)
    project_name = common.camel_case(images_path.parent.name)
    return common.create_test_case_name(_id, sha1, project_name, optional_description)


def create_enriched_config(config_path: Path, out_path: Path, images_path: Path):
    """Copy config to out_path and enrich it by additional configurations.

    If config_path is None, default to the file named 'config.ini' at the local
    directory.
    The images are added to the enriched config, as some operating systems
    limit the command line length.

    Return the path to the enriched config.
    """
    default_config_path = Path('.') / 'config.ini'
    config_path = config_path or default_config_path
    if not config_path.exists():
        print(f'Config expected at {config_path.absolute()} but not found.')
        exit -1
    path_of_enriched_config = out_path / enriched_config_name
    shutil.copy(config_path, path_of_enriched_config)
    with open(path_of_enriched_config, 'a') as f:
        f.write('\n')
        f.write(create_input_block_for_config(images_path))
    return path_of_enriched_config


def lazy_test_pipeline(app_path: Path,
                       out_root_path: Path,
                       images_path: Path,
                       optional_description: str = None,
                       config_path: Path = None,
                       reuse_id = False, # re-use last id to indicate that qa test case belongs to same batch
                       live_output = True):
    repo = common.Repo(app_path)
    out_path = out_root_path / get_lazytp_test_case_name(repo=repo,
                                                         out_path=out_root_path,
                                                         images_path=images_path,
                                                         optional_description=optional_description,
                                                         reuse_id=reuse_id)
    out_path.mkdir()

    path_of_enriched_config = create_enriched_config(config_path, out_path=out_path, images_path=images_path)

    # add patch to output containing changes all the way from last commit on main branch
    patch_not_on_main_branch = repo.get_patch(_from=repo.get_merge_base('HEAD', repo.guess_main_branch()))
    if patch_not_on_main_branch:
        with open(out_path / 'changesNotOnMainBranch.patch', 'w') as patch_file:
            patch_file.write(patch_not_on_main_branch)

    # add patch to output containing the last changes
    untracked_patch = repo.get_untracked_changes()
    if untracked_patch:
        with open(out_path / 'untrackedChanges.patch', 'w') as patch_file:
            patch_file.write(untracked_patch)

    output = test_pipeline(app_path = app_path,
                           out_path = out_path,
                           config_path = path_of_enriched_config,
                           live_output=live_output)

    rename_stitched_tiff(out_path)

    return output # for testing purposes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description =
           """
           lazy_tp, test_pipeline for lazy people.

           This script calls test_pipeline, checks for a stale binary, writes
           the results to an automatically generated output folder that tracks
           version information of the binary.
           """,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-x', '--test-pipeline',
        help='Path to test_pipeline executable. Assumed to be somewhere inside the rag repo.'
    )

    parser.add_argument(
        '-o', '--out-path',
        help='Path to where the output should be stored. The script will add a new sub-directory.'
    )

    parser.add_argument(
        '-i', '--images-path',
        help='Path to the \'images\' directory. The parent folder name will be used to name the output sub-directory.'
    )

    parser.add_argument(
        '-d', '--description',
        help='Optional description. It will be appended to the output folder name.'
    )

    parser.add_argument('--no-confirmation', action='store_true')

    args = vars(parser.parse_args())

    required_arg_names = ('test_pipeline', 'out_path', 'images_path')
    missing_required_arg_names = [name for name in required_arg_names if args[name] is None]
    argument_name_to_flag = lambda name : '--' + name.replace('_', '-')
    if missing_required_arg_names:
        print("Missing required arguments: ", [argument_name_to_flag(name) for name in missing_required_arg_names])
        parser.print_help()
        sys.exit(-1)

    check_executable(Path(args['test_pipeline']), prompt_user_confirmation=not args['no_confirmation'])

    lazy_test_pipeline(app_path = Path(args['test_pipeline']),
                       out_root_path = Path(args['out_path']),
                       images_path = Path(args['images_path']),
                       optional_description=args['description'])
