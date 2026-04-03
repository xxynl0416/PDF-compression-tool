# -*- coding: utf-8 -*-
"""
GUI样式模块 - 统一管理应用程序样式

配色方案: 现代柔和蓝色系
- 主色调: #4A90D9 (柔和蓝)
- 强调色: #2ECC71 (清新绿)
- 警告色: #E74C3C (柔和红)
- 背景色: #F8FAFC (浅灰白)
- 文字色: #2C3E50 (深灰)
"""

# ============================================================
# 配色定义
# ============================================================
COLORS = {
    # 主色调
    'primary': '#4A90D9',
    'primary_hover': '#3A7BC8',
    'primary_pressed': '#2E6DA4',

    # 成功/强调色
    'success': '#2ECC71',
    'success_hover': '#27AE60',
    'success_pressed': '#1E8449',

    # 警告/错误色
    'danger': '#E74C3C',
    'danger_hover': '#C0392B',
    'danger_pressed': '#A93226',

    # 警告色
    'warning': '#F39C12',
    'warning_hover': '#E67E22',

    # 信息色
    'info': '#3498DB',

    # 中性色
    'background': '#F8FAFC',
    'surface': '#FFFFFF',
    'surface_hover': '#F1F5F9',
    'border': '#E2E8F0',
    'border_focus': '#4A90D9',

    # 文字色
    'text_primary': '#2C3E50',
    'text_secondary': '#64748B',
    'text_disabled': '#94A3B8',
    'text_inverse': '#FFFFFF',

    # 进度条渐变
    'progress_start': '#4A90D9',
    'progress_end': '#2ECC71',
}


# ============================================================
# 全局样式
# ============================================================
GLOBAL_STYLE = f"""
/* 全局设置 */
QWidget {{
    font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif;
    font-size: 13px;
    color: {COLORS['text_primary']};
}}

QMainWindow {{
    background-color: {COLORS['background']};
}}

/* 滚动条样式 */
QScrollBar:vertical {{
    background: {COLORS['surface']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['text_secondary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""


# ============================================================
# 卡片样式
# ============================================================
CARD_STYLE = f"""
QWidget#card {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 16px;
}}
"""


# ============================================================
# 标签样式
# ============================================================
TITLE_STYLE = f"""
QLabel {{
    font-size: 22px;
    font-weight: bold;
    color: {COLORS['text_primary']};
    padding: 8px 0px;
}}
"""

SUBTITLE_STYLE = f"""
QLabel {{
    font-size: 14px;
    color: {COLORS['text_secondary']};
    padding: 4px 0px;
}}
"""

LABEL_STYLE = f"""
QLabel {{
    font-size: 13px;
    color: {COLORS['text_primary']};
}}
"""


# ============================================================
# 按钮样式
# ============================================================
BUTTON_BASE = f"""
QPushButton {{
    font-size: 14px;
    font-weight: 600;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
}}

QPushButton:hover {{
    background-color: {COLORS['surface_hover']};
}}

QPushButton:pressed {{
    background-color: {COLORS['border']};
}}

QPushButton:disabled {{
    background-color: {COLORS['surface_hover']};
    color: {COLORS['text_disabled']};
}}
"""

BUTTON_PRIMARY = f"""
QPushButton {{
    font-size: 14px;
    font-weight: 600;
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    background-color: {COLORS['success']};
    color: {COLORS['text_inverse']};
}}

QPushButton:hover {{
    background-color: {COLORS['success_hover']};
}}

QPushButton:pressed {{
    background-color: {COLORS['success_pressed']};
}}

QPushButton:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_disabled']};
}}
"""

BUTTON_SECONDARY = f"""
QPushButton {{
    font-size: 14px;
    font-weight: 500;
    padding: 10px 16px;
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
}}

QPushButton:hover {{
    background-color: {COLORS['surface_hover']};
    border-color: {COLORS['primary']};
    color: {COLORS['primary']};
}}

QPushButton:pressed {{
    background-color: {COLORS['border']};
}}

QPushButton:disabled {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_disabled']};
    border-color: {COLORS['border']};
}}
"""

BUTTON_DANGER = f"""
QPushButton {{
    font-size: 14px;
    font-weight: 500;
    padding: 10px 16px;
    border: none;
    border-radius: 8px;
    background-color: {COLORS['danger']};
    color: {COLORS['text_inverse']};
}}

QPushButton:hover {{
    background-color: {COLORS['danger_hover']};
}}

QPushButton:pressed {{
    background-color: {COLORS['danger_pressed']};
}}

QPushButton:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_disabled']};
}}
"""


# ============================================================
# 输入框样式
# ============================================================
LINE_EDIT_STYLE = f"""
QLineEdit {{
    font-size: 13px;
    padding: 10px 14px;
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['primary']};
    selection-color: {COLORS['text_inverse']};
}}

QLineEdit:hover {{
    border-color: {COLORS['text_secondary']};
}}

QLineEdit:focus {{
    border-color: {COLORS['primary']};
    background-color: {COLORS['surface']};
}}

QLineEdit:read-only {{
    background-color: {COLORS['background']};
}}

QLineEdit::placeholder {{
    color: {COLORS['text_disabled']};
}}
"""


# ============================================================
# 进度条样式
# ============================================================
PROGRESS_BAR_STYLE = f"""
QProgressBar {{
    font-size: 12px;
    font-weight: 500;
    border: none;
    border-radius: 6px;
    background-color: {COLORS['border']};
    color: {COLORS['text_inverse']};
    text-align: center;
    height: 24px;
}}

QProgressBar::chunk {{
    border-radius: 6px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['progress_start']},
        stop:1 {COLORS['progress_end']}
    );
}}
"""


# ============================================================
# 分组框样式
# ============================================================
GROUP_BOX_STYLE = f"""
QGroupBox {{
    font-size: 14px;
    font-weight: 600;
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    background-color: {COLORS['surface']};
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 8px;
    background-color: {COLORS['surface']};
    color: {COLORS['primary']};
}}
"""


# ============================================================
# 滑块样式
# ============================================================
SLIDER_STYLE = f"""
QSlider::groove:horizontal {{
    border: none;
    height: 6px;
    background: {COLORS['border']};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background: {COLORS['primary']};
    border-radius: 9px;
    border: 2px solid {COLORS['surface']};
}}

QSlider::handle:horizontal:hover {{
    background: {COLORS['primary_hover']};
}}

QSlider::handle:horizontal:pressed {{
    background: {COLORS['primary_pressed']};
}}

QSlider::sub-page:horizontal {{
    background: {COLORS['primary']};
    border-radius: 3px;
}}
"""


# ============================================================
# 复选框样式
# ============================================================
CHECKBOX_STYLE = f"""
QCheckBox {{
    font-size: 13px;
    color: {COLORS['text_primary']};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {COLORS['border']};
    background-color: {COLORS['surface']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['primary']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
}}

QCheckBox::indicator:checked:hover {{
    background-color: {COLORS['primary_hover']};
}}

QCheckBox::indicator:disabled {{
    background-color: {COLORS['surface_hover']};
    border-color: {COLORS['border']};
}}
"""


# ============================================================
# 消息框样式
# ============================================================
MESSAGE_BOX_STYLE = f"""
QMessageBox {{
    background-color: {COLORS['surface']};
}}

QMessageBox QLabel {{
    color: {COLORS['text_primary']};
    font-size: 13px;
}}

QMessageBox QPushButton {{
    min-width: 80px;
    padding: 8px 16px;
}}
"""


# ============================================================
# 文件拖放区域样式
# ============================================================
FILE_DROP_STYLE = f"""
QLineEdit {{
    font-size: 13px;
    padding: 12px 16px;
    border: 2px dashed {COLORS['border']};
    border-radius: 10px;
    background-color: {COLORS['background']};
    color: {COLORS['text_secondary']};
}}

QLineEdit:hover {{
    border-color: {COLORS['primary']};
    background-color: {COLORS['surface']};
}}

QLineEdit:focus {{
    border-color: {COLORS['primary']};
    border-style: solid;
}}

QLineEdit::placeholder {{
    color: {COLORS['text_disabled']};
}}
"""


# ============================================================
# 结果显示区域样式
# ============================================================
RESULT_SUCCESS_STYLE = f"color: {COLORS['success']}; font-weight: bold;"
RESULT_ERROR_STYLE = f"color: {COLORS['danger']}; font-weight: bold;"
RESULT_INFO_STYLE = f"color: {COLORS['info']}; font-weight: bold;"


# ============================================================
# 状态栏样式
# ============================================================
STATUS_BAR_STYLE = f"""
QStatusBar {{
    font-size: 12px;
    color: {COLORS['text_secondary']};
    background-color: {COLORS['surface']};
    border-top: 1px solid {COLORS['border']};
    padding: 4px 8px;
}}
"""


# ============================================================
# 组合样式函数
# ============================================================
def get_app_style() -> str:
    """获取应用程序完整样式表"""
    return "\n".join([
        GLOBAL_STYLE,
        STATUS_BAR_STYLE,
        MESSAGE_BOX_STYLE,
    ])


def get_card_style() -> str:
    """获取卡片样式"""
    return CARD_STYLE


def get_button_style(style_type: str = 'base') -> str:
    """获取按钮样式

    Args:
        style_type: 'base', 'primary', 'secondary', 'danger'
    """
    styles = {
        'base': BUTTON_BASE,
        'primary': BUTTON_PRIMARY,
        'secondary': BUTTON_SECONDARY,
        'danger': BUTTON_DANGER,
    }
    return styles.get(style_type, BUTTON_BASE)