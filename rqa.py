#/bin/python3

# Notes: The terms QA datasets and QA projects are used interchangeably and
# refer, depending on the context, to the set of images that belong to one project or
# the folder containing all information for the project, including the images).

import sys
import os
import logging
from pathlib import Path
from argparse import ArgumentParser
from itertools import chain

logging.basicConfig(level=logging.DEBUG)



def _contains_tiffs(path):
    files = chain(path.glob('*.tif'), path.glob('*.tiff'), path.glob('*.jpg'), path.glob('*.jpeg')) # TODO: collect extensions somewhere and iterate here if possible
    try: next(files);     return True
    except StopIteration: return False

class QAProject():
    """Class that represents a QA project.
    
    It is initialized from a path to the QA project folder. This folder is
    assumed to contain a subfolder called 'Images' in which the dataset is
    stored as a set of images:
        DataFolder
          |
          +-Images
              |
              +-img-001.tiff
              |
              +-img-002.tiff
              |
              +-...
    """
    def __init__(self, path):
        logging.debug(f"QAProject:{path=}")
        self.path = path
        self._check()

    def _check(self):
        images_path = self.path / 'Images'

        if not images_path.exists() or not images_path.is_dir():
            logging.debug(f"{self.path} not a valid project folder, missing images folder {images_path.name} ") # TODO: use __str__ instead of self.path
            return False
                
        if not _contains_tiffs(images_path):
            logging.debug(f"{images_path} does not contain tiff-files.")
            return False
        
        return True

        
if __name__ == "__main__":
    parser = ArgumentParser(
       description = 'this is the rapid qa description'
    )

    parser.add_argument(
        "qa_data",
         help = "path to the QA data projects"
    )

    if len(sys.argv) < 2:
        parser.print_help()
        
    arguments = parser.parse_args()
    data_root = Path(arguments.qa_data)
    data_projects = (path for path in data_root.iterdir() if path.is_dir())

    for project in data_projects:
        QAProject(project)