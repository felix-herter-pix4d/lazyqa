#!/usr/bin/python3
# process test_pipeline for batch of test projects

import lazytp as ltp

import argparse
import sys
from itertools import chain
from pathlib import Path

def contains_images(folder: Path):
    image_extensions = ('tif', 'TIF', 'tiff', 'TIFF', 'jpg', 'JPG', 'jpeg', 'JPEG')
    files = chain(*(folder.glob(f'*.{extension}') for extension in image_extensions))
    try: next(files);     return True
    except StopIteration: return False


class CannotGuessInputImagesFolderException(Exception):
    pass

def guess_images_subfolder(folder: Path):
    """Guess which sub-folder contains the input images.

    If there is a sub-folder named 'images', return a path to it.
    Else, if there is a single sub-folder containing images, return a path to it.
    Else return None

    Raises `CannotGuessInputImagesFolderException` if there is no sub-folder named 'images
    and there is none or more than one sub-folders containing images.
    """
    candidates = []
    for subfolder in folder.iterdir():
        if subfolder.is_dir():
            if subfolder.name == 'images':
                return subfolder
            elif contains_images(subfolder):
                candidates.append(subfolder)

    if len(candidates) == 1:
        return candidates[0]
    else:
        raise CannotGuessInputImagesFolderException(
            f'In {folder}: Found {len(candidates)} sub-folders in containing images (expected 1):\n'
            f'{[c.name for c in candidates]}')


def gather_input_paths_from_qa_projects_root(projects_root: Path):
    """Return the paths to the input images sub-folders for each QA project in `projects_root`.

    `projects_root` should be a directory containing a set of QA projects, each in it's own
    folder. For each of these folders, guess which sub-folder contains the images. Take note of any
    folders where the images sub-folder is not found or ambiguous and return a dict
    {'images_paths': list(Path), 'ambiguous_qa_projects': list(Path)}.
    """
    images_paths = []
    ambiguous_qa_projects = []
    candidates = (subfolder for subfolder in projects_root.iterdir() if subfolder.is_dir())
    for c in candidates:
        try:
            images_paths.append(guess_images_subfolder(c))
        except CannotGuessInputImagesFolderException:
            ambiguous_qa_projects.append(c)
    return {'images_paths': images_paths, 'ambiguous_qa_projects': ambiguous_qa_projects}


def gather_batchltp_arguments(qa_projects_root_path: Path,
                             app_path: Path,
                             out_root_path: Path,
                             config_path: Path,
                             optional_description: Path = None):
    """Return a valid input list for `batch_ltp` with `images_path`s gathered from `qa_projects_root_path`."""
    images_paths = gather_input_paths_from_qa_projects_root(qa_projects_root_path)['images_paths']
    return [{'app_path': app_path,
             'out_root_path': out_root_path,
             'images_path': image_path,
             'optional_description': optional_description,
             'config_path': config_path}
            for image_path in images_paths]


def batch_ltp(ltp_arguments: list[dict]):
    """Call lazy_tp on a batch of projects.

    `ltp_arguments` is a list of dictionaries, each containing the inputs for a call to
    lazytp.lazy_tp().
    """
    ltp_arguments = list(ltp_arguments)
    yield ltp.lazy_test_pipeline(**(ltp_arguments[0]))
    for args in ltp_arguments[1:]:
        yield ltp.lazy_test_pipeline(**args, reuse_id=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description =
           """
           batch_ltp, batch test_pipeline for lazy people.

           This script calls lazy_tp for each (QA) project in a projects root
           folder. For convenience, it checks for a stale binary, writes each
           of the results to an automatically generated output folder that
           tracks version information of the binary.

           Each project as assumed to reside in it's own folder in the projects
           root folder. The input images for a project need to reside in a sub-folder
           named 'images', unless there is only a single folder containing any images.
           The this unique folder it assumed to contain the input images.
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
        '-p', '--projects_path',
        help='Path to the root folder containing the QA projects.'
    )

    parser.add_argument(
        '-d', '--description',
        help='Optional description. It will be appended to the output folder names.'
    )

    parser.add_argument('--no-confirmation', action='store_true')

    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(-1)

    ltp.check_executable(Path(args.test_pipeline), prompt_user_confirmation=not args.no_confirmation)

    gen = batch_ltp(gather_batchltp_arguments(qa_projects_root_path=Path(args.projects_path),
                                             app_path=Path(args.test_pipeline),
                                             out_root_path=Path(args.out_path),
                                             config_path=Path('./config.ini'),
                                             optional_description=args.description))
    # trigger all computations
    for _ in gen:
        pass