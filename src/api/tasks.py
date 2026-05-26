"""任务生命周期路由 Blueprint"""
import os
import re
import uuid
from pathlib import Path

from flask import Blueprint, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename

from ..core.analyzer import PDFAnalyzer
from ..utils.file_utils import validate_pdf, format_size

tasks_bp = Blueprint('tasks', __name__)

_VALID_MODES = {'fast', 'balanced', 'high_quality'}
_VALID_BACKENDS = {'auto', 'python', 'ghostscript'}
_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


def _validate_compress_params(data: dict) -> str:
    task_id = data.get('task_id')
    if not task_id or not _UUID_RE.match(str(task_id)):
        return '无效的任务ID格式'

    target_size = data.get('target_size')
    if target_size is not None:
        try:
            target_size = float(target_size)
        except (TypeError, ValueError):
            return 'target_size 必须为数字'
        if not (10 <= target_size <= 500):
            return 'target_size 必须在 10~500 之间'

    quality = data.get('quality')
    if quality is not None:
        try:
            quality = int(quality)
        except (TypeError, ValueError):
            return 'quality 必须为整数'
        if not (30 <= quality <= 100):
            return 'quality 必须在 30~100 之间'

    compression_mode = data.get('compression_mode')
    if compression_mode is not None and compression_mode not in _VALID_MODES:
        return f'compression_mode 必须为 {"、".join(sorted(_VALID_MODES))} 之一'

    backend = data.get('backend')
    if backend is not None and backend not in _VALID_BACKENDS:
        return f'backend 必须为 {"、".join(sorted(_VALID_BACKENDS))} 之一'

    return ''


def init_tasks_blueprint(app, db, config, runner, limiter):
    """初始化任务 Blueprint 并注册到 app"""

    def allowed_file(filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}

    @tasks_bp.route('/')
    def index():
        return send_from_directory('templates', 'index.html')

    @tasks_bp.route('/api/upload', methods=['POST'])
    @limiter.limit("20 per hour")
    def upload_file():
        if 'file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': '只支持PDF文件'}), 400

        task_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        input_path = app.config['UPLOAD_FOLDER'] / f"{task_id}_{filename}"
        file.save(str(input_path))

        if not validate_pdf(str(input_path)):
            os.remove(str(input_path))
            return jsonify({'error': '无效的PDF文件'}), 400

        analyzer = PDFAnalyzer()
        try:
            info = analyzer.quick_check(str(input_path))
        except Exception as e:
            os.remove(str(input_path))
            return jsonify({'error': f'无法读取PDF文件: {str(e)}'}), 400
        file_info = {'size_mb': info['file_size_mb'], 'page_count': info['page_count']}

        db.create_task(
            task_id=task_id,
            filename=filename,
            input_path=str(input_path),
            file_info=file_info,
            target_size=config.target_size_mb,
            quality=config.default_quality,
            force_compress=True,
            compression_mode=config.compression_mode,
            backend=config.compression_backend
        )

        return jsonify({
            'task_id': task_id,
            'filename': filename,
            'defaults': {
                'target_size': config.target_size_mb,
                'quality': config.default_quality,
                'compression_mode': config.compression_mode,
                'backend': config.compression_backend,
            },
            'file_info': {
                'size_mb': round(info['file_size_mb'], 2),
                'size_formatted': format_size(info['file_size_mb']),
                'page_count': info['page_count']
            }
        })

    @tasks_bp.route('/api/compress', methods=['POST'])
    @limiter.limit("30 per hour")
    def start_compress():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': '请求体必须为有效JSON'}), 400

        validation_error = _validate_compress_params(data)
        if validation_error:
            return jsonify({'error': validation_error}), 400

        task_id = data.get('task_id')
        task = db.get_task(task_id)
        if not task:
            return jsonify({'error': '无效的任务ID'}), 400

        target_size = data.get('target_size', config.target_size_mb)
        quality = data.get('quality', config.default_quality)
        force_compress = data.get('force_compress', True)
        compression_mode = data.get('compression_mode', config.compression_mode)
        backend = data.get('backend', config.compression_backend)

        db.update_task_params(task_id, target_size, quality, force_compress, compression_mode, backend)

        # 原子状态转换，防止并发重复启动
        if not db.start_task(task_id):
            return jsonify({'error': '任务已在处理中或状态异常'}), 400

        import threading
        thread = threading.Thread(
            target=runner.run,
            args=(task_id, task['input_path'], target_size, quality, force_compress, compression_mode, backend)
        )
        thread.daemon = True
        thread.start()

        return jsonify({'message': '压缩任务已启动', 'task_id': task_id})

    @tasks_bp.route('/api/status/<task_id>')
    def get_status(task_id):
        task = db.get_task(task_id)
        if not task:
            return jsonify({'error': '无效的任务ID'}), 400
        response = {'task_id': task_id, 'status': task['status'], 'progress': task.get('progress', 0), 'message': task.get('message', '')}
        if task['status'] == 'completed' and task.get('result'):
            result = task['result']
            response['result'] = {
                'success': result['success'],
                'original_size_mb': round(result['original_size_mb'], 2),
                'final_size_mb': round(result['final_size_mb'], 2),
                'original_size_formatted': format_size(result['original_size_mb']),
                'final_size_formatted': format_size(result['final_size_mb']),
                'compression_ratio': round(result['compression_ratio'] * 100, 1),
                'was_split': result['was_split'],
                'message': result['message'],
                'output_files': [Path(f).name for f in result.get('output_files', [])],
                'compression_mode': result.get('compression_mode', config.compression_mode),
                'backend': result.get('backend', config.compression_backend)
            }
        elif task['status'] == 'failed' and task.get('result'):
            response['result'] = task['result']
        return jsonify(response)

    @tasks_bp.route('/api/download/<task_id>')
    def download_file(task_id):
        task = db.get_task(task_id)
        if not task:
            return jsonify({'error': '无效的任务ID'}), 400
        if task['status'] != 'completed':
            return jsonify({'error': '任务未完成'}), 400
        result = task.get('result', {})
        output_files = result.get('output_files', [])
        if not output_files:
            return jsonify({'error': '没有输出文件'}), 400
        if len(output_files) == 1:
            file_path = output_files[0]
            if not os.path.exists(file_path):
                return jsonify({'error': '输出文件不存在'}), 404
            return send_file(file_path, as_attachment=True, download_name=Path(file_path).name)

        import io, zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in output_files:
                zipf.write(file_path, Path(file_path).name)
        zip_buffer.seek(0)
        filename = Path(task['filename']).stem + '_compressed.zip'
        return send_file(zip_buffer, as_attachment=True, download_name=filename, mimetype='application/zip')

    @tasks_bp.route('/api/cleanup/<task_id>', methods=['DELETE'])
    def cleanup_task(task_id):
        task = db.get_task(task_id)
        if not task:
            return jsonify({'error': '无效的任务ID'}), 400
        input_path = task.get('input_path')
        if input_path and os.path.exists(input_path):
            os.remove(input_path)
        result = task.get('result') or {}
        output_files = result.get('output_files', [])
        for file_path in output_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        db.delete_task(task_id)
        return jsonify({'message': '清理完成'})

    @tasks_bp.route('/api/cancel/<task_id>', methods=['POST'])
    def cancel_task(task_id):
        task = db.get_task(task_id)
        if not task:
            return jsonify({'error': '无效的任务ID'}), 400
        # 原子取消，防止竞态
        if not db.cancel_task(task_id):
            return jsonify({'error': '任务不在处理中'}), 400
        runner.cancel(task_id)
        from ..websocket_manager import emit_task_failed
        emit_task_failed(task_id, '用户取消')
        return jsonify({'message': '取消请求已发送'})

    @tasks_bp.route('/api/tasks', methods=['GET'])
    def list_tasks():
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status', None)
        tasks = db.get_all_tasks(limit=limit, offset=offset, status_filter=status)
        simplified_tasks = []
        for task in tasks:
            simplified_tasks.append({
                'id': task['id'],
                'filename': task['filename'],
                'status': task['status'],
                'progress': task.get('progress', 0),
                'created_at': task['created_at'],
                'file_info': task.get('file_info', {}),
                'compression_mode': task.get('compression_mode', config.compression_mode),
                'backend': task.get('backend', config.compression_backend),
            })
        return jsonify({'tasks': simplified_tasks, 'total': len(simplified_tasks)})

    @tasks_bp.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory('static', filename)

    app.register_blueprint(tasks_bp)
