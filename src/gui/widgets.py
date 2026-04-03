# -*- coding: utf-8 -*-
"""自定义GUI组件 - 应用现代样式"""
from pathlib import Path
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget,
    QLineEdit,
    QPushButton,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QGroupBox,
    QSlider,
    QCheckBox,
    QFrame,
    QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

from .styles import (
    COLORS,
    FILE_DROP_STYLE,
    GROUP_BOX_STYLE,
    SLIDER_STYLE,
    CHECKBOX_STYLE,
    RESULT_SUCCESS_STYLE,
    RESULT_ERROR_STYLE,
    RESULT_INFO_STYLE,
)


class CardWidget(QFrame):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)


class FileDropEdit(QLineEdit):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText("拖放PDF文件到此处或点击浏览...")
        self.setReadOnly(True)
        self.setMinimumHeight(44)
        self.setStyleSheet(FILE_DROP_STYLE)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(FILE_DROP_STYLE.replace(
                f"border: 2px dashed {COLORS['border']}",
                f"border: 2px dashed {COLORS['primary']}"
            ))
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(FILE_DROP_STYLE)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(FILE_DROP_STYLE)
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith('.pdf'):
                self.setText(file_path)
                self.file_dropped.emit(file_path)
            else:
                self.setText("请选择PDF文件")


class FileInfoWidget(CardWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        self.size_icon = QLabel("📄")
        self.size_icon.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        layout.addWidget(self.size_icon)
        self.size_label = QLabel("文件大小: -")
        self.size_label.setStyleSheet(f"QLabel {{ color: {COLORS['text_primary']}; font-weight: 500; border: none; background: transparent; }}")
        layout.addWidget(self.size_label)
        layout.addWidget(self._create_separator())
        self.pages_icon = QLabel("📑")
        self.pages_icon.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        layout.addWidget(self.pages_icon)
        self.pages_label = QLabel("页数: -")
        self.pages_label.setStyleSheet(f"QLabel {{ color: {COLORS['text_primary']}; font-weight: 500; border: none; background: transparent; }}")
        layout.addWidget(self.pages_label)
        layout.addWidget(self._create_separator())
        self.images_icon = QLabel("🖼")
        self.images_icon.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        layout.addWidget(self.images_icon)
        self.images_label = QLabel("图像: -")
        self.images_label.setStyleSheet(f"QLabel {{ color: {COLORS['text_primary']}; font-weight: 500; border: none; background: transparent; }}")
        layout.addWidget(self.images_label)
        layout.addStretch()

    def _create_separator(self) -> QLabel:
        sep = QLabel("│")
        sep.setStyleSheet(f"color: {COLORS['border']}; border: none; background: transparent; margin: 0 4px;")
        return sep

    def update_info(self, size_mb: float, pages: int, images: int):
        self.size_label.setText(f"文件大小: {self._format_size(size_mb)}")
        self.pages_label.setText(f"页数: {pages}")
        self.images_label.setText(f"图像: {images}")

    def clear_info(self):
        self.size_label.setText("文件大小: -")
        self.pages_label.setText("页数: -")
        self.images_label.setText("图像: -")

    def _format_size(self, size_mb: float) -> str:
        return f"{size_mb / 1024:.2f} GB" if size_mb >= 1024 else f"{size_mb:.2f} MB"


class ProgressWidget(CardWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimumHeight(28)
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(f"QLabel {{ color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent; }}")
        layout.addWidget(self.status_label)

    def set_progress(self, value: int, message: str = ""):
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)

    def reset(self):
        self.progress_bar.setValue(0)
        self.status_label.setText("就绪")

    def set_max(self, maximum: int):
        self.progress_bar.setMaximum(maximum)


class SettingsWidget(QGroupBox):
    settings_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("⚙ 压缩设置", parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(GROUP_BOX_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(14)

        size_container = QWidget()
        size_layout = QHBoxLayout(size_container)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(12)
        size_label = QLabel("目标大小")
        size_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 500;")
        size_layout.addWidget(size_label)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(50)
        self.size_slider.setMaximum(500)
        self.size_slider.setValue(200)
        self.size_slider.setTickPosition(QSlider.TicksBelow)
        self.size_slider.setTickInterval(50)
        self.size_slider.setStyleSheet(SLIDER_STYLE)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        size_layout.addWidget(self.size_slider, stretch=1)
        self.size_value_label = QLabel("200 MB")
        self.size_value_label.setMinimumWidth(75)
        self.size_value_label.setStyleSheet(f"QLabel {{ color: {COLORS['primary']}; font-weight: 600; font-size: 14px; }}")
        size_layout.addWidget(self.size_value_label)
        layout.addWidget(size_container)

        quality_container = QWidget()
        quality_layout = QHBoxLayout(quality_container)
        quality_layout.setContentsMargins(0, 0, 0, 0)
        quality_layout.setSpacing(12)
        quality_label = QLabel("图像质量")
        quality_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 500;")
        quality_layout.addWidget(quality_label)
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setMinimum(50)
        self.quality_slider.setMaximum(100)
        self.quality_slider.setValue(85)
        self.quality_slider.setTickPosition(QSlider.TicksBelow)
        self.quality_slider.setTickInterval(10)
        self.quality_slider.setStyleSheet(SLIDER_STYLE)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(self.quality_slider, stretch=1)
        self.quality_value_label = QLabel("85%")
        self.quality_value_label.setMinimumWidth(75)
        self.quality_value_label.setStyleSheet(f"QLabel {{ color: {COLORS['primary']}; font-weight: 600; font-size: 14px; }}")
        quality_layout.addWidget(self.quality_value_label)
        layout.addWidget(quality_container)

        mode_container = QWidget()
        mode_layout = QHBoxLayout(mode_container)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(12)
        mode_label = QLabel("压缩模式")
        mode_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 500;")
        mode_layout.addWidget(mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("快速模式", "fast")
        self.mode_combo.addItem("平衡模式", "balanced")
        self.mode_combo.addItem("高质量模式", "high_quality")
        self.mode_combo.currentIndexChanged.connect(lambda _: self.settings_changed.emit())
        mode_layout.addWidget(self.mode_combo, stretch=1)
        layout.addWidget(mode_container)

        backend_container = QWidget()
        backend_layout = QHBoxLayout(backend_container)
        backend_layout.setContentsMargins(0, 0, 0, 0)
        backend_layout.setSpacing(12)
        backend_label = QLabel("压缩后端")
        backend_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 500;")
        backend_layout.addWidget(backend_label)
        self.backend_combo = QComboBox()
        self.backend_combo.addItem("自动", "auto")
        self.backend_combo.addItem("Python", "python")
        self.backend_combo.addItem("Ghostscript", "ghostscript")
        self.backend_combo.currentIndexChanged.connect(lambda _: self.settings_changed.emit())
        backend_layout.addWidget(self.backend_combo, stretch=1)
        layout.addWidget(backend_container)

        options_container = QWidget()
        options_layout = QVBoxLayout(options_container)
        options_layout.setContentsMargins(0, 8, 0, 0)
        options_layout.setSpacing(10)
        self.auto_split_checkbox = QCheckBox("无法压缩到目标时自动分段")
        self.auto_split_checkbox.setChecked(True)
        self.auto_split_checkbox.setStyleSheet(CHECKBOX_STYLE)
        options_layout.addWidget(self.auto_split_checkbox)
        self.keep_original_checkbox = QCheckBox("保留原始文件")
        self.keep_original_checkbox.setChecked(True)
        self.keep_original_checkbox.setStyleSheet(CHECKBOX_STYLE)
        options_layout.addWidget(self.keep_original_checkbox)
        layout.addWidget(options_container)

    def _on_size_changed(self, value: int):
        self.size_value_label.setText(f"{value} MB")
        self.settings_changed.emit()

    def _on_quality_changed(self, value: int):
        self.quality_value_label.setText(f"{value}%")
        self.settings_changed.emit()

    def get_target_size(self) -> int:
        return self.size_slider.value()

    def get_quality(self) -> int:
        return self.quality_slider.value()

    def get_compression_mode(self) -> str:
        return self.mode_combo.currentData()

    def get_backend(self) -> str:
        return self.backend_combo.currentData()

    def is_auto_split_enabled(self) -> bool:
        return self.auto_split_checkbox.isChecked()

    def is_keep_original(self) -> bool:
        return self.keep_original_checkbox.isChecked()

    def set_defaults(self, target_size: int = 200, quality: int = 85, mode: str = 'fast', backend: str = 'auto'):
        self.size_slider.setValue(target_size)
        self.quality_slider.setValue(quality)
        mode_index = max(0, self.mode_combo.findData(mode))
        backend_index = max(0, self.backend_combo.findData(backend))
        self.mode_combo.setCurrentIndex(mode_index)
        self.backend_combo.setCurrentIndex(backend_index)


class ResultWidget(CardWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("QLabel { font-size: 15px; line-height: 1.6; border: none; background: transparent; }")
        layout.addWidget(self.result_label)
        self.files_label = QLabel()
        self.files_label.setWordWrap(True)
        self.files_label.setStyleSheet(f"QLabel {{ color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent; }}")
        layout.addWidget(self.files_label)

    def show_success(self, original_size: float, final_size: float, output_files: list, was_split: bool):
        compression_ratio = (1 - final_size / original_size) * 100 if original_size > 0 else 0
        if was_split:
            self.result_label.setText(
                f"<span style='{RESULT_SUCCESS_STYLE} font-size: 18px;'>分段完成!</span><br><br>"
                f"<span style='color: {COLORS['text_secondary']}'>原始大小:</span> "
                f"<span style='font-weight: 600;'>{self._format_size(original_size)}</span><br>"
                f"<span style='color: {COLORS['text_secondary']}'>已分为:</span> "
                f"<span style='font-weight: 600; color: {COLORS['success']}'>{len(output_files)} 个文件</span>"
            )
        else:
            self.result_label.setText(
                f"<span style='{RESULT_SUCCESS_STYLE} font-size: 18px;'>压缩完成!</span><br><br>"
                f"<span style='color: {COLORS['text_secondary']}'>原始大小:</span> "
                f"<span style='font-weight: 600;'>{self._format_size(original_size)}</span><br>"
                f"<span style='color: {COLORS['text_secondary']}'>压缩后:</span> "
                f"<span style='font-weight: 600; color: {COLORS['success']}'>{self._format_size(final_size)}</span><br>"
                f"<span style='color: {COLORS['text_secondary']}'>体积减少:</span> "
                f"<span style='font-weight: 600; color: {COLORS['primary']}'>{compression_ratio:.1f}%</span>"
            )
        if len(output_files) > 1:
            files_text = "<br>".join(f"<span style='color: {COLORS['primary']}'>•</span> {Path(f).name}" for f in output_files)
            self.files_label.setText(f"<b>输出文件:</b><br>{files_text}")
        else:
            self.files_label.setText(f"<b>输出文件:</b> {Path(output_files[0]).name}")

    def show_error(self, message: str):
        self.result_label.setText(
            f"<span style='{RESULT_ERROR_STYLE} font-size: 18px;'>处理失败</span><br><br>"
            f"<span style='color: {COLORS['text_secondary']}'>{message}</span>"
        )
        self.files_label.clear()

    def show_no_need(self, size: float, target: float):
        self.result_label.setText(
            f"<span style='{RESULT_INFO_STYLE} font-size: 18px;'>无需处理</span><br><br>"
            f"<span style='color: {COLORS['text_secondary']}'>文件大小</span> "
            f"<span style='font-weight: 600; color: {COLORS['info']}'>{self._format_size(size)}</span> "
            f"<span style='color: {COLORS['text_secondary']}'>已小于目标</span> "
            f"<span style='font-weight: 600;'>{self._format_size(target)}</span>"
        )
        self.files_label.clear()

    def clear(self):
        self.result_label.clear()
        self.files_label.clear()

    def _format_size(self, size_mb: float) -> str:
        return f"{size_mb / 1024:.2f} GB" if size_mb >= 1024 else f"{size_mb:.2f} MB"
