import os
import threading
import pytest
from localstack import config
from localstack.services import infra
from localstack.constants import ENV_INTERNAL_TEST_RUN
from localstack.utils.common import cleanup, safe_requests, FuncThread
from localstack.utils.analytics.profiler import profiled
from .test_terraform import TestTerraform

mutex = threading.Semaphore(0)


@pytest.fixture(scope='session', autouse=True)
def setup_and_teardown_package():
    try:
        os.environ[ENV_INTERNAL_TEST_RUN] = '1'
        # disable SSL verification for local tests
        safe_requests.verify_ssl = False
        # start profiling
        FuncThread(start_profiling).start()
        # start infrastructure services
        infra.start_infra(asynchronous=True)
        # initialize certain tests asynchronously to reduce overall test time
        if not os.environ.get('TEST_PATH') or 'terraform' in os.environ.get('TEST_PATH'):
            TestTerraform.init_async()
    except Exception as e:
        # make sure to tear down the infrastructure
        infra.stop_infra()
        raise e
    yield

    # teardown_package
    print('Shutdown')
    mutex.release()
    cleanup(files=True)
    infra.stop_infra()


def start_profiling(*args):
    if not config.USE_PROFILER:
        return

    @profiled()
    def profile_func():
        # keep profiler active until tests have finished
        mutex.acquire()

    print('Start profiling...')
    profile_func()
    print('Done profiling...')