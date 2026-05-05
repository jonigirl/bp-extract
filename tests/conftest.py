import pytest

import config as config_module


@pytest.fixture(autouse=True)
def reset_config_singleton():
    config_module._config_instance = None
    yield
    config_module._config_instance = None
