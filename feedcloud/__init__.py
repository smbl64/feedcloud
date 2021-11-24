from . import log_setup, settings

settings.update_settings_from_env_vars()
log_setup.config()
