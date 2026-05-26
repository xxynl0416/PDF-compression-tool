"""后台压缩任务运行器"""
import os
import traceback

from ..core.compressor import PDFCompressor
from ..database.task_db import TaskDatabase
from ..websocket_manager import emit_task_progress, emit_task_completed, emit_task_failed


class TaskCancelled(Exception):
    pass


class TaskRunner:
    """管理后台压缩任务的执行和取消"""

    def __init__(self, db: TaskDatabase, config):
        self.db = db
        self.config = config
        self._cancelled: set = set()

    def cancel(self, task_id: str):
        self._cancelled.add(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        return task_id in self._cancelled

    def run(self, task_id: str, input_path: str, target_size: int, quality: int,
            force_compress: bool = True, compression_mode: str = 'fast', backend: str = 'auto'):
        try:
            self.db.update_task_status(task_id, 'processing', progress=0, message='开始压缩')
            emit_task_progress(task_id, 0, '开始压缩', 'processing')

            def progress_callback(progress: int, message: str):
                if task_id in self._cancelled:
                    self._cancelled.discard(task_id)
                    raise TaskCancelled('用户取消了任务')
                self.db.update_task_status(task_id, 'processing', progress=progress, message=message)
                emit_task_progress(task_id, progress, message, 'processing')

            compressor = PDFCompressor(
                target_size_mb=target_size,
                quality=quality,
                progress_callback=progress_callback,
                force_compress=force_compress,
                compression_mode=compression_mode,
                backend=backend,
                ghostscript_path=self.config.ghostscript_path or None,
                output_suffix=self.config.output_suffix,
                split_enabled=self.config.split_enabled,
            )

            result = compressor.compress(input_path)

            result_data = {
                'success': result.success,
                'original_size_mb': result.original_size_mb,
                'final_size_mb': result.final_size_mb,
                'output_files': result.output_files if result.output_files else [],
                'was_split': result.was_split,
                'message': result.message if result.message else '压缩完成',
                'compression_ratio': result.compression_ratio,
                'final_quality': getattr(result, 'final_quality', 85),
                'final_dpi': getattr(result, 'final_dpi', 96),
                'compression_mode': compression_mode,
                'backend': backend,
            }

            self.db.update_task_result(task_id, result_data)

            if result.success:
                self.db.update_task_status(task_id, 'completed', progress=100, message='压缩完成')
                emit_task_completed(task_id, result_data)
            else:
                self.db.update_task_status(task_id, 'failed', progress=0, message=result.message)
                emit_task_failed(task_id, result.message)

        except Exception as e:
            traceback.print_exc()
            is_cancelled = isinstance(e, TaskCancelled)
            error_msg = str(e) if not is_cancelled else '用户取消'
            self.db.update_task_status(task_id, 'failed', progress=0, message=error_msg)
            self.db.update_task_result(task_id, {
                'success': False,
                'message': error_msg,
                'original_size_mb': 0,
                'final_size_mb': 0,
                'compression_ratio': 1.0,
                'was_split': False,
                'output_files': []
            })
            emit_task_failed(task_id, error_msg)
            if os.path.exists(input_path):
                try:
                    os.remove(input_path)
                except OSError:
                    pass
