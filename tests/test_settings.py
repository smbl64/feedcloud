import os

from feedcloud import constants, settings


def test_update_from_env_vars():
    settings.SOME_BOOL = True
    settings.SOME_INT = 1
    settings.SOME_STR = "first"

    os.environ[constants.SETTINGS_ENV_PREFIX + "SOME_BOOL"] = "false"
    os.environ[constants.SETTINGS_ENV_PREFIX + "SOME_INT"] = "2"
    os.environ[constants.SETTINGS_ENV_PREFIX + "SOME_STR"] = "second"

    settings.update_settings_from_env_vars()

    assert not settings.SOME_BOOL
    assert settings.SOME_INT == 2
    assert settings.SOME_STR == "second"


def test_update_from_dict():
    settings.FOOBAR = 42

    settings.update_settings_from_dict(dict(FOOBAR=50))

    assert settings.FOOBAR == 50
    del settings.FOOBAR
