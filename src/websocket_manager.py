# -*- coding: utf-8 -*-
"""
WebSocket 管理器 - 实时进度推送
"""
import logging
from flask_socketio import SocketIO, emit

logger = logging.getLogger("websocket_manager")

socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')


def init_socketio(app):
    """初始化 SocketIO"""
    socketio.init_app(app)
    return socketio


def join_task_room(task_id):
    """加入任务房间"""
    from flask_socketio import join_room

    room_name = f"task_{task_id}"
    join_room(room_name)
    return room_name


def leave_task_room(task_id):
    """离开任务房间"""
    from flask_socketio import leave_room

    room_name = f"task_{task_id}"
    leave_room(room_name)


def emit_task_update(task_id, data, namespace='/'):
    """发送任务更新"""
    room_name = f"task_{task_id}"
    socketio.emit('task_update', {
        'task_id': task_id,
        **data
    }, room=room_name, namespace=namespace)


def emit_task_progress(task_id, progress, message, status='processing'):
    """发送进度更新"""
    emit_task_update(task_id, {
        'progress': progress,
        'message': message,
        'status': status
    })


def emit_task_completed(task_id, result):
    """发送任务完成通知"""
    emit_task_update(task_id, {
        'status': 'completed',
        'progress': 100,
        'message': '压缩完成',
        'result': result
    })


def emit_task_failed(task_id, error_message):
    """发送任务失败通知"""
    emit_task_update(task_id, {
        'status': 'failed',
        'progress': 0,
        'message': error_message
    })


@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')
    return True


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    logger.info('客户端已断开')


@socketio.on('join_task')
def on_join_task(data):
    """客户端加入任务房间"""
    task_id = data.get('task_id')
    if task_id:
        join_task_room(task_id)
        emit('joined', {'task_id': task_id})


@socketio.on('leave_task')
def on_leave_task(data):
    """客户端离开任务房间"""
    task_id = data.get('task_id')
    if task_id:
        leave_task_room(task_id)
