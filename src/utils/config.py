"""配置管理模块"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG = {
    'compression': {
        'target_size_mb': 200,
        'default_quality': 85,
        'min_quality': 50,
        'max_dpi': 300,
        'mode': 'fast',
        'backend': 'auto',
        'ghostscript_path': '',
    },
    'split': {
        'enabled': True,
        'max_size_mb': 200,
    },
    'output': {
        'suffix': '_compressed',
        'segment_suffix': '_part',
        'keep_original': True,
    },
    'logging': {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    }
}


class Config:
    """配置管理类"""

    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}

    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = DEFAULT_CONFIG.copy()
        return cls._instance

    def load_from_file(self, config_path: str) -> bool:
        try:
            import yaml
            path = Path(config_path)
            if not path.exists():
                return False
            with open(path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
            if loaded_config:
                self._deep_update(self._config, loaded_config)
            return True
        except Exception:
            return False

    def _deep_update(self, base: dict, update: dict):
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    @property
    def target_size_mb(self) -> float:
        return self.get('compression.target_size_mb', 200)

    @property
    def default_quality(self) -> int:
        return self.get('compression.default_quality', 85)

    @property
    def min_quality(self) -> int:
        return self.get('compression.min_quality', 50)

    @property
    def max_dpi(self) -> int:
        return self.get('compression.max_dpi', 300)

    @property
    def compression_mode(self) -> str:
        return self.get('compression.mode', 'fast')

    @property
    def compression_backend(self) -> str:
        return self.get('compression.backend', 'auto')

    @property
    def ghostscript_path(self) -> str:
        return self.get('compression.ghostscript_path', '')

    @property
    def split_enabled(self) -> bool:
        return self.get('split.enabled', True)

    @property
    def split_max_size_mb(self) -> float:
        return self.get('split.max_size_mb', 200)

    @property
    def output_suffix(self) -> str:
        return self.get('output.suffix', '_compressed')

    @property
    def segment_suffix(self) -> str:
        return self.get('output.segment_suffix', '_part')

    @property
    def keep_original(self) -> bool:
        return self.get('output.keep_original', True)

    @property
    def log_level(self) -> str:
        return self.get('logging.level', 'INFO')

    @property
    def log_format(self) -> str:
        return self.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def get_config() -> Config:
    return Config()


def load_config(config_path: Optional[str] = None) -> Config:
    config = get_config()
    if config_path:
        config.load_from_file(config_path)
    else:
        default_paths = [
            Path.cwd() / 'config.yaml',
            Path(__file__).parent.parent.parent / 'config.yaml',
        ]
        for path in default_paths:
            if path.exists():
                config.load_from_file(str(path))
                break
    return config
