# process test_pipeline for batch of test projects

import lazytp as ltp

from itertools import chain
from pathlib import Path

def contains_images(folder: Path):
    image_extensions = ('tif', 'TIF', 'tiff', 'TIFF', 'jpg', 'JPG', 'jpeg', 'JPEG')
    files = chain(*(folder.glob(f'*.{extension}') for extension in image_extensions))
    try: next(files);     return True
    except StopIteration: return False


class AmbiguousQAProjectLayoutException(Exception):
    pass


def guess_images_subfolder(folder: Path):
    """Guess which sub-folder contains the input images.

    If there is a sub-folder named 'images', return a path to it.
    Else, if there is a single sub-folder containing images, return a path to it.
    Else return None

    Raises an `AmbiguousQAProjectLayoutException` if there is no sub-folder named 'images
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
        raise AmbiguousQAProjectLayoutException(
            f'In {folder}: Found {len(candidates)} sub-folders in containing images (expected 1):\n'
            f'{[c.name for c in candidates]}')


def batch_ltp(ltp_arguments: list[dict]):
    for args in ltp_arguments:
        yield ltp.lazy_test_pipeline(**args)