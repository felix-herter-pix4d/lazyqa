import lazytp as ltp
from test_helpers import *

def test_calling_test_pipeline_calls_the_expected_command(environment_for_test_pipeline):
    env = environment_for_test_pipeline
    command_triggered = ltp.test_pipeline(app_path = env['app_path'],
                                          out_path = env['out_path'],
                                          config_path = env['config_path'])

    expected_command = f"{env['app_path']} -f {env['config_path']} -o {env['out_path']}"
                         #' '.join(str(image_path) for image_path in env['images_path'].glob('*')))
    assert command_triggered == expected_command


