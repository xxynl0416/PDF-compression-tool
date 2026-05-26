"""管理路由 Blueprint"""
from flask import Blueprint, request, jsonify

admin_bp = Blueprint('admin', __name__)


def init_admin_blueprint(app, db, limiter):
    """初始化管理 Blueprint 并注册到 app"""

    @admin_bp.route('/api/stats', methods=['GET'])
    @limiter.limit("60 per hour")
    def get_stats():
        return jsonify(db.get_task_stats())

    @admin_bp.route('/api/cleanup-old', methods=['POST'])
    @limiter.limit("5 per hour")
    def cleanup_old_tasks():
        payload = request.get_json(silent=True) or {}
        hours = payload.get('hours', 24)
        try:
            hours = int(hours)
        except (TypeError, ValueError):
            return jsonify({'error': 'hours 必须为整数'}), 400
        if not (1 <= hours <= 8760):
            return jsonify({'error': 'hours 必须在 1~8760 之间'}), 400
        deleted = db.cleanup_old_tasks(hours)
        return jsonify({'message': f'已清理 {deleted} 个过期任务', 'deleted': deleted})

    app.register_blueprint(admin_bp)
