"""API 路由测试"""
import sys
import json
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


class TestIndexRoute:

    def test_index_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200


class TestCompressValidation:

    def test_compress_rejects_empty_body(self, client):
        response = client.post('/api/compress', data='', content_type='application/json')
        assert response.status_code == 400
        assert 'JSON' in response.get_json()['error']

    def test_compress_rejects_invalid_task_id(self, client):
        response = client.post('/api/compress', json={'task_id': 'not-a-uuid'})
        assert response.status_code == 400
        assert '任务ID' in response.get_json()['error']

    def test_compress_rejects_invalid_target_size(self, client):
        import uuid
        task_id = str(uuid.uuid4())
        response = client.post('/api/compress', json={
            'task_id': task_id,
            'target_size': 9999
        })
        assert response.status_code == 400
        assert 'target_size' in response.get_json()['error']

    def test_compress_rejects_invalid_quality(self, client):
        import uuid
        task_id = str(uuid.uuid4())
        response = client.post('/api/compress', json={
            'task_id': task_id,
            'quality': 5
        })
        assert response.status_code == 400
        assert 'quality' in response.get_json()['error']

    def test_compress_rejects_invalid_mode(self, client):
        import uuid
        task_id = str(uuid.uuid4())
        response = client.post('/api/compress', json={
            'task_id': task_id,
            'compression_mode': 'turbo'
        })
        assert response.status_code == 400
        assert 'compression_mode' in response.get_json()['error']

    def test_compress_rejects_invalid_backend(self, client):
        import uuid
        task_id = str(uuid.uuid4())
        response = client.post('/api/compress', json={
            'task_id': task_id,
            'backend': 'cuda'
        })
        assert response.status_code == 400
        assert 'backend' in response.get_json()['error']

    def test_compress_rejects_nonexistent_task(self, client):
        import uuid
        task_id = str(uuid.uuid4())
        response = client.post('/api/compress', json={
            'task_id': task_id,
            'target_size': 200,
            'quality': 85,
            'compression_mode': 'fast',
            'backend': 'auto'
        })
        assert response.status_code == 400
        assert '无效的任务ID' in response.get_json()['error']


class TestStatusRoute:

    def test_status_rejects_invalid_task(self, client):
        response = client.get('/api/status/invalid-id')
        assert response.status_code == 400


class TestCleanupRoute:

    def test_cleanup_rejects_invalid_task(self, client):
        response = client.delete('/api/cleanup/invalid-id')
        assert response.status_code == 400


class TestCancelRoute:

    def test_cancel_rejects_invalid_task(self, client):
        response = client.post('/api/cancel/invalid-id')
        assert response.status_code == 400


class TestStatsRoute:

    def test_stats_returns_json(self, client):
        response = client.get('/api/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total' in data
        assert 'completed' in data


class TestTasksRoute:

    def test_tasks_returns_list(self, client):
        response = client.get('/api/tasks')
        assert response.status_code == 200
        data = response.get_json()
        assert 'tasks' in data
        assert 'total' in data
