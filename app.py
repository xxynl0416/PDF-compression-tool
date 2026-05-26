# -*- coding: utf-8 -*-
"""PDF压缩工具 - Web服务入口"""
import os
import sys
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config
from src.database.task_db import TaskDatabase
from src.websocket_manager import socketio, init_socketio
from src.tasks.runner import TaskRunner
from src.api.tasks import init_tasks_blueprint
from src.api.admin import init_admin_blueprint


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    CORS(app)
    init_socketio(app)

    config = load_config()
    db = TaskDatabase()
    runner = TaskRunner(db, config)
    limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
    app.config['OUTPUT_FOLDER'] = Path(__file__).parent / 'outputs'
    app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
    app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
    app.config['OUTPUT_FOLDER'].mkdir(parents=True, exist_ok=True)

    init_tasks_blueprint(app, db, config, runner, limiter)
    init_admin_blueprint(app, db, limiter)

    return app, socketio


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == '__main__':
    app, socketio_app = create_app()
    config = load_config()

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
