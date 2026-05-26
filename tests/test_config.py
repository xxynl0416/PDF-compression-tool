"""配置模块测试"""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config, load_config, get_config


@pytest.fixture(autouse=True)
def reset_singleton():
    """每个测试前重置 Config 单例"""
    Config._instance = None
    yield
    Config._instance = None


class TestConfig:

    def test_singleton_returns_same_instance(self):
        c1 = Config()
        c2 = Config()
        assert c1 is c2

    def test_default_values(self):
        config = Config()
        assert config.target_size_mb == 200
        assert config.default_quality == 85
        assert config.min_quality == 50
        assert config.compression_mode == 'fast'
        assert config.compression_backend == 'auto'
        assert config.split_enabled is True
        assert config.output_suffix == '_compressed'

    def test_get_nested_key(self):
        config = Config()
        assert config.get('compression.target_size_mb') == 200
        assert config.get('split.enabled') is True

    def test_get_with_default(self):
        config = Config()
        assert config.get('nonexistent.key', 'fallback') == 'fallback'

    def test_set_and_get(self):
        config = Config()
        config.set('compression.target_size_mb', 100)
        assert config.get('compression.target_size_mb') == 100

    def test_set_creates_nested_keys(self):
        config = Config()
        config.set('new.nested.key', 42)
        assert config.get('new.nested.key') == 42

    def test_load_from_yaml_file(self):
        config = Config()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("compression:\n  target_size_mb: 150\n  default_quality: 70\n")
            f.flush()
            result = config.load_from_file(f.name)
            assert result is True
            assert config.target_size_mb == 150
            assert config.default_quality == 70
        Path(f.name).unlink()

    def test_load_from_nonexistent_file(self):
        config = Config()
        result = config.load_from_file('/nonexistent/path.yaml')
        assert result is False

    def test_load_preserves_unspecified_defaults(self):
        config = Config()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("compression:\n  target_size_mb: 300\n")
            f.flush()
            config.load_from_file(f.name)
            assert config.target_size_mb == 300
            assert config.default_quality == 85  # default preserved
        Path(f.name).unlink()

    def test_ghostscript_path_default_empty(self):
        config = Config()
        assert config.ghostscript_path == ''

    def test_segment_suffix_property(self):
        config = Config()
        assert config.segment_suffix == '_part'
