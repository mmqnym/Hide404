import os
import toml

from share.types import Config

_CONFIG: Config = None


def _validate_fields(config: dict) -> None:
    """
    Validates the configuration file has all required fields and values

    Returns:
        None
    """

    openai_api_key = config.get("openai").get("api_key")

    if not openai_api_key:
        raise KeyError("The openai.api_key is required")

    openai_base_url = config.get("openai").get("base_url")

    if not openai_base_url:
        raise KeyError("The openai.base_url is required")

    # TODO: Add more validation


def _translate_config(config: Config) -> None:
    """
    Translates and updates the configuration object as needed.

    Args:
        config (Config): The configuration object to translate and update.

    Returns:
        None
    """

    if config.server.workers == -1:
        config.server.workers = os.cpu_count()


def _load_config() -> Config:
    """
    Reads and returns the configuration from ./config/config.toml

    Returns:
        Config: The configuration object
    """

    config = None

    try:
        config = toml.load("./config/config.toml")
        _validate_fields(config)
        config_obj = Config.parse(config)
        _translate_config(config_obj)
    except KeyError as e:
        raise Exception(
            f"The config.toml file is missing some required fields and/or values: {e}"
        )
    except Exception as e:
        raise Exception(f"Failed to read config.toml: {e}")

    return config_obj


def get_config() -> Config:
    """
    Retrieves the global configuration object.

    Returns:
        Config: The application's configuration object.
    """

    global _CONFIG
    if not _CONFIG:
        _CONFIG = _load_config()
    return _CONFIG
