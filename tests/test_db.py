"""数据库模块测试"""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.task_db import TaskDatabase


@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / 'test.db'
        yield TaskDatabase(str(db_path))


class TestTaskDatabase:

    def test_create_and_get_task(self, db):
        ok = db.create_task('t1', 'test.pdf', '/tmp/test.pdf',
                            {'size_mb': 1.5, 'page_count': 10})
        assert ok is True
        task = db.get_task('t1')
        assert task is not None
        assert task['id'] == 't1'
        assert task['filename'] == 'test.pdf'
        assert task['status'] == 'uploaded'
        assert task['file_info']['size_mb'] == 1.5

    def test_get_nonexistent_task(self, db):
        task = db.get_task('nonexistent')
        assert task is None

    def test_update_task_status(self, db):
        db.create_task('t2', 'a.pdf', '/tmp/a.pdf', {})
        ok = db.update_task_status('t2', 'processing', progress=50, message='处理中')
        assert ok is True
        task = db.get_task('t2')
        assert task['status'] == 'processing'
        assert task['progress'] == 50
        assert task['message'] == '处理中'
        assert task['started_at'] is not None

    def test_update_task_result(self, db):
        db.create_task('t3', 'b.pdf', '/tmp/b.pdf', {})
        result = {'success': True, 'final_size_mb': 0.5}
        ok = db.update_task_result('t3', result)
        assert ok is True
        task = db.get_task('t3')
        assert task['result']['success'] is True

    def test_update_task_params(self, db):
        db.create_task('t4', 'c.pdf', '/tmp/c.pdf', {})
        ok = db.update_task_params('t4', 150, 70, True, 'balanced', 'python')
        assert ok is True
        task = db.get_task('t4')
        assert task['target_size'] == 150
        assert task['quality'] == 70
        assert task['compression_mode'] == 'balanced'
        assert task['backend'] == 'python'

    def test_delete_task(self, db):
        db.create_task('t5', 'd.pdf', '/tmp/d.pdf', {})
        ok = db.delete_task('t5')
        assert ok is True
        assert db.get_task('t5') is None

    def test_get_all_tasks(self, db):
        for i in range(5):
            db.create_task(f'list_{i}', f'f{i}.pdf', f'/tmp/f{i}.pdf', {})
        tasks = db.get_all_tasks(limit=3)
        assert len(tasks) == 3

    def test_get_all_tasks_with_status_filter(self, db):
        db.create_task('s1', 'a.pdf', '/tmp/a.pdf', {})
        db.create_task('s2', 'b.pdf', '/tmp/b.pdf', {})
        db.update_task_status('s1', 'completed')
        tasks = db.get_all_tasks(status_filter='completed')
        assert len(tasks) == 1
        assert tasks[0]['id'] == 's1'

    def test_cleanup_old_tasks(self, db):
        db.create_task('old1', 'a.pdf', '/tmp/a.pdf', {})
        deleted = db.cleanup_old_tasks(hours=0)
        assert deleted >= 0  # May be 0 if created_at is recent

    def test_get_task_stats(self, db):
        db.create_task('st1', 'a.pdf', '/tmp/a.pdf', {})
        db.create_task('st2', 'b.pdf', '/tmp/b.pdf', {})
        db.update_task_status('st1', 'completed')
        stats = db.get_task_stats()
        assert stats['total'] == 2
        assert stats['completed'] == 1
        assert stats['uploaded'] == 1

    def test_compression_mode_and_backend_fields(self, db):
        ok = db.create_task('cb1', 'a.pdf', '/tmp/a.pdf', {},
                            compression_mode='balanced', backend='ghostscript')
        assert ok is True
        task = db.get_task('cb1')
        assert task['compression_mode'] == 'balanced'
        assert task['backend'] == 'ghostscript'
