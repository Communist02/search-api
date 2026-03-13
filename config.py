import json
import os
from typing import Any

required_fields = [
    'auth_api_url',
    'debug_mode',
    'opensearch_host',
    'opensearch_port',
    'db_user',
    'db_password',
    'opensearch_user',
    'opensearch_password',
]

default_config = {
    'auth_api_url': "http://localhost:8080",
    # 'auth_api_url': "http://minio-s3-1.eco.dvo.ru:8080",
    'debug_mode': True,
    'opensearch_host': "elastic-1.eco.dvo.ru",
    'opensearch_port': 9200,
    'db_user': "root",
    'db_password': "root",
    'opensearch_user': "admin",
    'opensearch_password': "OTFiZDkwMGRiOWQw1!"
}


class Config:
    def __init__(self, config_path=os.path.expanduser('~/storage_api_config.json')):
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
                print(f"Config loaded from: {config_path}")
                self._validate_required_fields()
        except FileNotFoundError:
            print(f"Config file not found at {config_path}")
            self.config = default_config
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in config file at {config_path}: {e}")
            self.config = default_config

    def validate_required_fields(self):
        """Проверяет наличие всех обязательных полей"""
        missing_fields = []

        for field in required_fields:
            if field not in self.config or self.config.get(field) is None:
                missing_fields.append(field)

        if missing_fields:
            print(
                f"Missing required fields: {', '.join(missing_fields)}")
        else:
            print("All required fields are present")

    def __getattr__(self, name: str) -> Any:
        return self.config.get(name)

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)


config = Config()
