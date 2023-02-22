#!/usr/bin/python3

import helpers

import logging
import subprocess
from argparse import ArgumentParser
from pathlib import Path

binary = '~/Code/pix4d-rag/build-fastmap-Release/bin/test_pipeline'
out_path = Path('/home/fherter/Tickets/cv412_GpuMspFullBlending/Output')
#datapath = r'../Data/Hay\ Beach\ Dunes\ Test\ 050818_inputs' # with spaces
data_path = Path('../Data/Hay_BeachDunesTest050818_inputs')

def execute_command(command: list[str]):
    subprocess_result = subprocess.run(command, capture_output=True, shell=True)
    msg = subprocess_result.stdout
    msg = msg.decode('utf-8').strip()
    try:
        subprocess_result.check_returncode()
        return msg
    except subprocess.CalledProcessError:
        raise RuntimeError(f"failed executing binary '{command.split()[0]} ...':\n'{msg}'")


def test_pipeline(app_path: Path,
                  out_path: Path,
                  config_path: Path,
                  images_path: Path):
    command = str(app_path)
    command += ' -f ' + str(config_path)
    command += ' -o ' + str(out_path)
    command += ' ' + ' '.join(str(image_path) for image_path in images_path.glob('*'))
    return execute_command(command)


def lazy_test_pipeline(app_path: Path,
                       out_path: Path,
                       images_path: Path,
                       optional_description: str = None):
    # TODO: extract into function
    _id = helpers.get_next_id(out_path)
    sha1 = helpers.Repo(app_path).get_sha_of_branch('HEAD', short=True)
    project_name = helpers.camel_case(images_path.parent.name)
    out_subfolder_name = helpers.create_test_case_name(_id, sha1, project_name, optional_description)
    out_subfolder_path = out_path / out_subfolder_name
    out_subfolder_path.mkdir()

    return test_pipeline(app_path = app_path,
                         out_path = out_subfolder_path,
                         config_path = Path('./config.txt'),
                         images_path = images_path)

if __name__ == '__main__':
    pass