#!/usr/bin/python3

import helpers

import argparse
import logging
import subprocess
import sys
from pathlib import Path

binary = '~/Code/pix4d-rag/build-fastmap-Release/bin/test_pipeline'
out_path = Path('/home/fherter/Tickets/cv412_GpuMspFullBlending/Output')
#datapath = r'../Data/Hay\ Beach\ Dunes\ Test\ 050818_inputs' # with spaces
data_path = Path('../Data/Hay_BeachDunesTest050818_inputs')

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
    return execute_command(command)


def derive_stitched_result_name(test_case_name: str):
    """Derived name has the form '<id>_<optionalDescription>_stitched.tiff'.'"""
    parsed = helpers.parse_test_case_name(test_case_name)
    components = [parsed['id']]
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


def lazy_test_pipeline(app_path: Path,
                       out_path: Path,
                       images_path: Path,
                       optional_description: str = None):
    # TODO: extract into function
    _id = helpers.get_next_id(out_path)
    sha1 = helpers.Repo(app_path).get_sha_of_branch('HEAD', short=True)
    project_name = helpers.camel_case(images_path.parent.name)
    test_case_name = helpers.create_test_case_name(_id, sha1, project_name, optional_description)
    out_subfolder_path = out_path / test_case_name
    out_subfolder_path.mkdir()

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

    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    lazy_test_pipeline(app_path = Path(args.test_pipeline),
                       out_path = Path(args.out_path),
                       images_path = Path(args.images_path),
                       optional_description=args.description)