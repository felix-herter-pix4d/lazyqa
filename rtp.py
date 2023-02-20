#!/usr/bin/python3

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
    print(f'msg is: {msg}')
    try:
        subprocess_result.check_returncode()
        return msg
    except subprocess.CalledProcessError:
        raise RuntimeError(f"failed executing binary '{command.split()[0]} ...':\n'{msg}'")

if __name__ == '__main__':
    images = [str(image_path) for image_path in data_path.glob('*')]
    out_args = ['-o', str(out_path / '02_')]

    result = execute_command(' '.join([binary] + out_args + images))
    print("result is: ", result)