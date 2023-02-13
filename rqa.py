#/bin/python3

# Script to rapidly assess the effect that a code change has to a wide variety
# of test cases (QA datasets).
#
# It enables to compare the *new* results produced by the app with a
# *reference* output (usually produced the current state of the app).
#
# Notes: The terms QA datasets and QA projects are used interchangeably and
# refer, depending on the context, to the set of images that belong to one
# project or the folder containing all information for the project, including
# the images).

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
    @classmethod
    def _get_image_path(cls, project_root: Path):
        """Return path to subfolder of the project that should contain the images."""
        return project_root / 'Images'

    @classmethod
    def check(cls, path: Path):
        """Check that the requirements of a QAProject are met."""
        if not path.is_dir():
            logging.debug(f"Not a project '{path}': not a folder.")
            return False

        images_path = cls._get_image_path(path)

        if not images_path.exists() or not images_path.is_dir():
            logging.debug(f"Not a project '{path}': missing folder '{images_path.name}'.")
            return False
                
        if not _contains_tiffs(images_path):
            logging.debug(f"Not a project '{images_path}': no images found.")
            return False
        
        return True

    def __new__(cls, path: Path):
        """Ensure that the requirements of a QAProject are met before creating an instance."""
        if not cls.check(path):
            raise ValueError(f"Could not create {cls} from '{path}': requirements not met.")
        return super().__new__(cls)

    def __init__(self, path: Path):
        logging.info(f"Created QAProject:{path=}")
        self.path = path

def check_binary(binary: Path):
    """Sanity checks on the binary."""
    if not os.access(binary, os.X_OK):
        raise ValueError(f"'{binary}' is not executable")

    #TODO: compare touch time.

    return True

        
if __name__ == "__main__":
    parser = ArgumentParser(
       description = 'this is the rapid qa description'
    )

    parser.add_argument(
        "projects",
         help = "path to the QA data projects"
    )

    parser.add_argument(
        "binary",
         help = "path to the binary under investigation"
    )

    if len(sys.argv) < 2:
        parser.print_help()
        
    arguments = parser.parse_args()
    qa_projects_root = Path(arguments.projects)
    qa_projects = (QAProject(path) for path in qa_projects_root.iterdir() if QAProject.check(path))
    
    binary = Path(arguments.binary)
    check_binary(binary)
    
    stream = os.popen(f"git -C {binary.parent} rev-parse HEAD")
    output = stream.read()
    print("the output is: \n", output)