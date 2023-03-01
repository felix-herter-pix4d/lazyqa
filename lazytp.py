#!/usr/bin/python3

import helpers


import argparse
import datetime
import os
import subprocess
import time
import sys
from pathlib import Path


def execute_command(command: list[str], live_output: bool=False):
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               encoding='utf-8',
                               shell=True)
    output_lines = []
    for line in iter(process.stdout.readline, ''):
        if live_output:
            print(line, end='')
        output_lines.append(line.strip())
    return '\n'.join(output_lines)


def test_pipeline(app_path: Path,
                  out_path: Path,
                  config_path: Path,
                  images_path: Path):
    command = str(app_path)
    command += ' -f ' + str(config_path)
    command += ' -o ' + str(out_path)
    command += ' ' + ' '.join(str(image_path) for image_path in images_path.glob('*'))
    command += f' | tee {str(out_path / "log.txt")}'
    print('COMMAND:\n', command)
    return execute_command(command, live_output=True)


def derive_stitched_result_name(test_case_name: str):
    """Derived name has the form '<id>_<optionalDescription>_stitched.tiff'.'"""
    parsed = helpers.parse_test_case_name(test_case_name)
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

    # binary not executable?
    if not os.access(app_path, os.X_OK):
        print(f'{colors.red}',
              f'binary {app_path} is not executable',
              f'{colors.normal}')
        exit(-1)

    # binary not part of git repo?
    if not helpers.is_part_of_git_repo(app_path):
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


def get_lazytp_test_case_name(repo: helpers.Repo, out_path: Path, images_path: Path, optional_description: str=None):
    """Use as id one more than the largest qa test case id we find in the out_path.

    If all test cases were generated with lazytp this implies that they all have increasing ids.
    """
    _id = helpers.get_next_id(out_path)
    sha1 = repo.get_sha_of_branch('HEAD', short=True)
    project_name = helpers.camel_case(images_path.parent.name)
    return helpers.create_test_case_name(_id, sha1, project_name, optional_description)


def lazy_test_pipeline(app_path: Path,
                       out_path: Path,
                       images_path: Path,
                       optional_description: str = None):
    repo = helpers.Repo(app_path)
    out_subfolder_path = out_path / get_lazytp_test_case_name(repo=repo,
                                                              out_path=out_path,
                                                              images_path=images_path,
                                                              optional_description=optional_description)
    out_subfolder_path.mkdir()

    # add patch to output containing changes all the way from last commit on main branch
    patch_not_on_main_branch = repo.get_patch(_from=repo.get_merge_base('HEAD', repo.guess_main_branch()))
    if patch_not_on_main_branch:
        with open(out_subfolder_path / 'changesNotOnMainBranch.patch', 'w') as patch_file:
            patch_file.write(patch_not_on_main_branch)

    # add patch to output containing the last changes
    untracked_patch = repo.get_untracked_changes()
    if untracked_patch:
        with open(out_subfolder_path / 'untrackedChanges.patch', 'w') as patch_file:
            patch_file.write(untracked_patch)

    output = test_pipeline(app_path = app_path,
                           out_path = out_subfolder_path,
                           config_path = Path('./config.txt'),
                           images_path = images_path)

    rename_stitched_tiff(out_subfolder_path)

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
        '-i', '--images_path',
        help='Path to the \'images\' directory. The parent folder name will be used to name the output sub-directory.'
    )

    parser.add_argument(
        '-d', '--description',
        help='Optional description. It will be appended to the output folder name.'
    )

    parser.add_argument('--no-confirmation', action='store_true')

    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(-1)

    check_executable(Path(args.test_pipeline), prompt_user_confirmation=not args.no_confirmation)

    lazy_test_pipeline(app_path = Path(args.test_pipeline),
                       out_path = Path(args.out_path),
                       images_path = Path(args.images_path),
                       optional_description=args.description)
