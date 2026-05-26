"""管理路由 Blueprint"""
from flask import Blueprint, request, jsonify

admin_bp = Blueprint('admin', __name__)


def init_admin_blueprint(app, db, limiter):
    """初始化管理 Blueprint 并注册到 app"""

    @admin_bp.route('/api/stats', methods=['GET'])
    def get_stats():
        return jsonify(db.get_task_stats())

    @admin_bp.route('/api/cleanup-old', methods=['POST'])
    def cleanup_old_tasks():
        payload = request.get_json(silent=True) or {}
        hours = payload.get('hours', 24)
        deleted = db.cleanup_old_tasks(hours)
        return jsonify({'message': f'已清理 {deleted} 个过期任务', 'deleted': deleted})

    app.register_blueprint(admin_bp)
