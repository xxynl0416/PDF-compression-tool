# -*- coding: utf-8 -*-
"""
数据库模型 - 持久化任务存储
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class TaskDatabase:
    """任务数据库管理器"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'data' / 'tasks.db'
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    input_path TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'uploaded',
                    progress INTEGER DEFAULT 0,
                    message TEXT DEFAULT '',
                    file_info TEXT,
                    result TEXT,
                    target_size REAL,
                    quality INTEGER,
                    force_compress BOOLEAN DEFAULT 1,
                    compression_mode TEXT DEFAULT 'fast',
                    backend TEXT DEFAULT 'auto',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                )
            ''')

            existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
            if 'compression_mode' not in existing_columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN compression_mode TEXT DEFAULT 'fast'")
            if 'backend' not in existing_columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN backend TEXT DEFAULT 'auto'")

            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)')
            conn.commit()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_task(self, task_id: str, filename: str, input_path: str,
                    file_info: Dict[str, Any], target_size: float = 200,
                    quality: int = 85, force_compress: bool = True,
                    compression_mode: str = 'fast', backend: str = 'auto') -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT INTO tasks (
                        id, filename, input_path, status, progress, message,
                        file_info, target_size, quality, force_compress, compression_mode, backend, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id, filename, input_path, 'uploaded', 0, '文件已上传',
                    json.dumps(file_info, ensure_ascii=False),
                    target_size, quality, force_compress, compression_mode, backend,
                    datetime.now().isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"创建任务失败: {e}")
            return False

    def update_task_status(self, task_id: str, status: str, progress: int = None, message: str = None) -> bool:
        try:
            with self._get_connection() as conn:
                updates = ['status = ?']
                params = [status]
                if progress is not None:
                    updates.append('progress = ?')
                    params.append(progress)
                if message is not None:
                    updates.append('message = ?')
                    params.append(message)
                if status == 'processing':
                    updates.append('started_at = ?')
                    params.append(datetime.now().isoformat())
                elif status in ('completed', 'failed'):
                    updates.append('completed_at = ?')
                    params.append(datetime.now().isoformat())
                params.append(task_id)
                conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return True
        except Exception as e:
            print(f"更新任务状态失败: {e}")
            return False

    def update_task_result(self, task_id: str, result: Dict[str, Any]) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute('UPDATE tasks SET result = ? WHERE id = ?', (json.dumps(result, ensure_ascii=False), task_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"更新任务结果失败: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
        except Exception as e:
            print(f"获取任务失败: {e}")
            return None

    def get_all_tasks(self, limit: int = 50, offset: int = 0, status_filter: str = None) -> List[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                query = 'SELECT * FROM tasks'
                params = []
                if status_filter:
                    query += ' WHERE status = ?'
                    params.append(status_filter)
                query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
                params.extend([limit, offset])
                cursor = conn.execute(query, params)
                return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"获取任务列表失败: {e}")
            return []

    def delete_task(self, task_id: str) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"删除任务失败: {e}")
            return False

    def cleanup_old_tasks(self, hours: int = 24) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM tasks WHERE created_at < datetime('now', ?)", (f'-{hours} hours',))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"清理过期任务失败: {e}")
            return 0

    def get_task_stats(self) -> Dict[str, Any]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('''
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                           SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                           SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
                           SUM(CASE WHEN status = 'uploaded' THEN 1 ELSE 0 END) as uploaded
                    FROM tasks
                ''')
                row = cursor.fetchone()
                return {'total': row['total'], 'completed': row['completed'], 'failed': row['failed'], 'processing': row['processing'], 'uploaded': row['uploaded']}
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}

    def _row_to_dict(self, row) -> Dict[str, Any]:
        result = dict(row)
        if result.get('file_info'):
            try:
                result['file_info'] = json.loads(result['file_info'])
            except Exception:
                result['file_info'] = {}
        if result.get('result'):
            try:
                result['result'] = json.loads(result['result'])
            except Exception:
                result['result'] = {}
        return result
