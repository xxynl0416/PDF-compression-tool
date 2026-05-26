"""API 成功路径测试"""
import sys
import json
import uuid
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCompressWithValidTask:

    def test_compress_starts_with_valid_task(self, client):
        """创建任务后发送压缩请求应成功启动"""
        # 先上传一个文件来创建任务
        import io
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< /Root 1 0 R >>\nstartxref\n0\n%%EOF'
        data = {'file': (io.BytesIO(pdf_content), 'test.pdf')}
        upload_resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
        assert upload_resp.status_code == 200
        task_id = upload_resp.get_json()['task_id']

        # 发送压缩请求
        compress_resp = client.post('/api/compress', json={
            'task_id': task_id,
            'target_size': 200,
            'quality': 85,
            'compression_mode': 'fast',
            'backend': 'auto'
        })
        assert compress_resp.status_code == 200
        data = compress_resp.get_json()
        assert 'task_id' in data

    def test_compress_rejects_already_processing(self, client):
        """同一个任务不能重复启动压缩"""
        import io
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< /Root 1 0 R >>\nstartxref\n0\n%%EOF'
        data = {'file': (io.BytesIO(pdf_content), 'test.pdf')}
        upload_resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
        task_id = upload_resp.get_json()['task_id']

        # 第一次压缩
        client.post('/api/compress', json={'task_id': task_id})

        # 第二次应被拒绝
        resp2 = client.post('/api/compress', json={'task_id': task_id})
        assert resp2.status_code == 400


class TestStatusWithValidTask:

    def test_status_returns_task_info(self, client):
        """有效任务的状态查询应返回完整信息"""
        import io
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< /Root 1 0 R >>\nstartxref\n0\n%%EOF'
        data = {'file': (io.BytesIO(pdf_content), 'test.pdf')}
        upload_resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
        task_id = upload_resp.get_json()['task_id']

        resp = client.get(f'/api/status/{task_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'uploaded'
        assert 'progress' in data
        assert 'message' in data


class TestCancelWithValidTask:

    def test_cancel_rejects_non_processing_task(self, client):
        """未在处理中的任务不能取消"""
        import io
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< /Root 1 0 R >>\nstartxref\n0\n%%EOF'
        data = {'file': (io.BytesIO(pdf_content), 'test.pdf')}
        upload_resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
        task_id = upload_resp.get_json()['task_id']

        resp = client.post(f'/api/cancel/{task_id}')
        assert resp.status_code == 400
        assert '不在处理中' in resp.get_json()['error']


class TestCleanupWithValidTask:

    def test_cleanup_deletes_task(self, client):
        """清理请求应删除任务"""
        import io
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< /Root 1 0 R >>\nstartxref\n0\n%%EOF'
        data = {'file': (io.BytesIO(pdf_content), 'test.pdf')}
        upload_resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
        task_id = upload_resp.get_json()['task_id']

        resp = client.delete(f'/api/cleanup/{task_id}')
        assert resp.status_code == 200

        # 再次查询应返回 400
        status_resp = client.get(f'/api/status/{task_id}')
        assert status_resp.status_code == 400


class TestAdminValidation:

    def test_cleanup_old_rejects_invalid_hours(self, client):
        resp = client.post('/api/cleanup-old', json={'hours': -1})
        assert resp.status_code == 400

    def test_cleanup_old_rejects_string_hours(self, client):
        resp = client.post('/api/cleanup-old', json={'hours': 'abc'})
        assert resp.status_code == 400

    def test_cleanup_old_accepts_valid_hours(self, client):
        resp = client.post('/api/cleanup-old', json={'hours': 24})
        assert resp.status_code == 200
        assert 'deleted' in resp.get_json()

    def test_stats_returns_expected_keys(self, client):
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total' in data
        assert 'completed' in data
        assert 'failed' in data
        assert 'processing' in data
        assert 'uploaded' in data
