# process test_pipeline for batch of test projects

import lazytp as ltp

def batch_ltp(ltp_arguments: list[dict]):
    for args in ltp_arguments:
        yield ltp.lazy_test_pipeline(**args)