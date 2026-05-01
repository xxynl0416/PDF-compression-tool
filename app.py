# -*- coding: utf-8 -*-
"""
PDF压缩工具 - Web服务
"""
import io
import os
import sys
import uuid
import zipfile
import threading
import traceback
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

sys.path.insert(0, str(Path(__file__).parent))

from src.core.compressor import PDFCompressor
from src.core.analyzer import PDFAnalyzer
from src.utils.file_utils import validate_pdf, format_size
from src.utils.config import load_config
from src.database.task_db import TaskDatabase
from src.websocket_manager import socketio, init_socketio, emit_task_progress, emit_task_completed, emit_task_failed

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
socketio_app = init_socketio(app)
config = load_config()

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['OUTPUT_FOLDER'] = Path(__file__).parent / 'outputs'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
app.config['OUTPUT_FOLDER'].mkdir(parents=True, exist_ok=True)

db = TaskDatabase()
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def env_bool(name: str, default: bool = False) -> bool:
    """Parse boolean environment variables with sane defaults."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def run_compression(task_id: str, input_path: str, target_size: int, quality: int,
                    force_compress: bool = True, compression_mode: str = 'fast', backend: str = 'auto'):
    try:
        db.update_task_status(task_id, 'processing', progress=0, message='开始压缩')
        emit_task_progress(task_id, 0, '开始压缩', 'processing')

        def progress_callback(progress: int, message: str):
            db.update_task_status(task_id, 'processing', progress=progress, message=message)
            emit_task_progress(task_id, progress, message, 'processing')

        compressor = PDFCompressor(
            target_size_mb=target_size,
            quality=quality,
            progress_callback=progress_callback,
            force_compress=force_compress,
            compression_mode=compression_mode,
            backend=backend,
            ghostscript_path=config.ghostscript_path or None
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

        db.update_task_result(task_id, result_data)

        if result.success:
            db.update_task_status(task_id, 'completed', progress=100, message='压缩完成')
            emit_task_completed(task_id, result_data)
        else:
            db.update_task_status(task_id, 'failed', progress=0, message=result.message)
            emit_task_failed(task_id, result.message)

    except Exception as e:
        traceback.print_exc()
        error_msg = str(e)
        db.update_task_status(task_id, 'failed', progress=0, message=error_msg)
        db.update_task_result(task_id, {
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


@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')


@app.route('/api/upload', methods=['POST'])
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
    info = analyzer.quick_check(str(input_path))
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


@app.route('/api/compress', methods=['POST'])
@limiter.limit("30 per hour")
def start_compress():
    data = request.json
    task_id = data.get('task_id')
    task = db.get_task(task_id)
    if not task:
        return jsonify({'error': '无效的任务ID'}), 400
    if task['status'] == 'processing':
        return jsonify({'error': '任务正在处理中'}), 400

    target_size = data.get('target_size', config.target_size_mb)
    quality = data.get('quality', config.default_quality)
    force_compress = data.get('force_compress', True)
    compression_mode = data.get('compression_mode', config.compression_mode)
    backend = data.get('backend', config.compression_backend)

    db.update_task_params(task_id, target_size, quality, force_compress, compression_mode, backend)

    thread = threading.Thread(
        target=run_compression,
        args=(task_id, task['input_path'], target_size, quality, force_compress, compression_mode, backend)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'message': '压缩任务已启动', 'task_id': task_id})


@app.route('/api/status/<task_id>')
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


@app.route('/api/download/<task_id>')
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

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in output_files:
            zipf.write(file_path, Path(file_path).name)
    zip_buffer.seek(0)
    filename = Path(task['filename']).stem + '_compressed.zip'
    return send_file(zip_buffer, as_attachment=True, download_name=filename, mimetype='application/zip')


@app.route('/api/cleanup/<task_id>', methods=['DELETE'])
def cleanup_task(task_id):
    task = db.get_task(task_id)
    if not task:
        return jsonify({'error': '无效的任务ID'}), 400
    input_path = task.get('input_path')
    if input_path and os.path.exists(input_path):
        os.remove(input_path)
    result = task.get('result', {})
    output_files = result.get('output_files', [])
    for file_path in output_files:
        if os.path.exists(file_path):
            os.remove(file_path)
    db.delete_task(task_id)
    return jsonify({'message': '清理完成'})


@app.route('/api/tasks', methods=['GET'])
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


@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify(db.get_task_stats())


@app.route('/api/cleanup-old', methods=['POST'])
def cleanup_old_tasks():
    payload = request.get_json(silent=True) or {}
    hours = payload.get('hours', 24)
    deleted = db.cleanup_old_tasks(hours)
    return jsonify({'message': f'已清理 {deleted} 个过期任务', 'deleted': deleted})


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


if __name__ == '__main__':
    host = os.getenv('PDFTOOL_HOST', '0.0.0.0')
    try:
        port = int(os.getenv('PDFTOOL_PORT', '5000'))
    except ValueError:
        port = 5000
    debug = env_bool('PDFTOOL_DEBUG', False)

    print("=" * 50)
    print("PDF压缩工具 Web服务")
    print("=" * 50)
    print(f"访问地址: http://{host}:{port}")
    print(f"默认模式: {config.compression_mode}, 默认后端: {config.compression_backend}")
    print(f"DEBUG: {debug}")
    print("=" * 50)
    socketio_app.run(app, host=host, port=port, debug=debug)
