"""共享测试配置"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

_app_instance = None
_socketio_instance = None


def _get_app():
    global _app_instance, _socketio_instance
    if _app_instance is None:
        from app import create_app
        _app_instance, _socketio_instance = create_app()
        _app_instance.config['TESTING'] = True
    return _app_instance


@pytest.fixture
def client():
    app = _get_app()
    with app.test_client() as client:
        yield client
