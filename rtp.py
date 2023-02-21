#!/usr/bin/python3

import rqa

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

if __name__ == '__main__':
    binary_path = Path(binary).expanduser()
    repo = rqa.Repo(Path(binary_path))

    if not out_path.exists():
        logging.info(f"output directory '{out_path}' not found, creating it")
        out_path.mkdir(parents=True)

    #images = [str(image_path) for image_path in data_path.glob('*')]
    #out_args = ['-o', str(out_path / '02_')]

    #result = execute_command(' '.join([binary] + out_args + images))
    #print("result is: ", result)