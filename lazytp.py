#!/usr/bin/python3

import common

import argparse
import shutil
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

    The images are added to the enriched config, as some operating systems
    limit the command line length.

    Return the path to the enriched config.
    """
    if not config_path.exists():
        print(f'Config expected at {config_path.absolute()} but not found.')
        sys.exit(-1)
    path_of_enriched_config = out_path / enriched_config_name
    shutil.copy(config_path, path_of_enriched_config)
    with open(path_of_enriched_config, 'a') as f:
        f.write('\n')
        f.write(create_input_block_for_config(images_path))
    return path_of_enriched_config


def lazy_test_pipeline(app_path: Path,
                       out_root_path: Path,
                       images_path: Path,
                       config_path: Path,
                       optional_description: str = None,
                       reuse_id = False, # re-use last id to indicate that qa test case belongs to same batch
                       live_output = True):
    """Create a folder for the output and write the test_pipeline results to it.

    The output folder will be a subfolder of `out_root_path` and will be named
    following the pattern,

        <id>_<sha1>_<datasetName>_<optionalDescription>
    e.g.
        003_1234567890_snowyHillside_increasedStepSizeTo42

    <id> is an index that is per default one larger then the largest <id> used
         in `out_root_path`.
    <sha1> is a short sha1 of the `test_pipeline` repo at the time
           `test_pipeline was called
    <datasetName> is the name of the dataset to which `images_path` belongs. This
                  is attempted to be derived automatically.
    <optionalDescription> is the `optionalDescription` sanitized into CamelCase.
    """
    repo = common.Repo(app_path)
    out_path = out_root_path / get_lazytp_test_case_name(repo=repo,
                                                         out_path=out_root_path,
                                                         images_path=images_path,
                                                         optional_description=optional_description,
                                                         reuse_id=reuse_id)
    out_path.mkdir()

    path_of_enriched_config = create_enriched_config(config_path, out_path=out_path, images_path=images_path)

    common.add_patch_not_on_main_branch(repo=repo, out_path=out_path)
    common.add_patch_dirty_state(repo=repo, out_path=out_path)

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
           version information.
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
        '-c', '--config',
        default = './config.ini',
        help='Path to the config.ini. Default is ./config.ini. Will be copied and expanded (see output folder).'
    )

    parser.add_argument(
        '-d', '--description',
        help='Optional description. It will be appended to the output folder name.'
    )

    parser.add_argument('--no-confirmation', action='store_true')

    args = vars(parser.parse_args())

    common.check_mandatory_arguments(mandatory_args=['test_pipeline', 'out_path', 'images_path'],
                                     argument_parser=parser)

    common.check_executable(Path(args['test_pipeline']), prompt_user_confirmation=not args['no_confirmation'])

    lazy_test_pipeline(app_path = Path(args['test_pipeline']),
                       out_root_path = Path(args['out_path']),
                       images_path = Path(args['images_path']),
                       config_path = Path(args['config']),
                       optional_description=args['description'])
