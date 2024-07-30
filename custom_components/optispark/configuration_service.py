import json
import os

from .const import LOGGER


class ConfigurationService:
    _instance = None
    _initialized = False
    _cache = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConfigurationService, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_file=None):
        if config_file and not ConfigurationService._initialized:
            self.config_file = config_file
            self.config_data = self._load_config()
            ConfigurationService._initialized = True

    def _load_config(self):
        script_path = os.path.abspath(__file__)
        parent_dir = os.path.dirname(script_path)
        file_path = os.path.join(parent_dir, self.config_file)
        try:
            with open(file_path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            LOGGER.error(f"Error: The configuration file {self.config_file} was not found.")
            return {}
        except json.JSONDecodeError:
            LOGGER.error(
                f"Error: The configuration file {self.config_file} is not a valid JSON."
            )
            return {}

    def get(self, path, default=None):
        if not ConfigurationService._initialized:
            raise Exception("ConfigurationService must be initialized with a config file before use.")

        if path in ConfigurationService._cache:
            return ConfigurationService._cache[path]

        keys = path.split('.')
        data = self.config_data
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, default)
            else:
                data = default

        # Cache the result before returning
        ConfigurationService._cache[path] = data
        return data


config_service = ConfigurationService(config_file='./config/config.json')
