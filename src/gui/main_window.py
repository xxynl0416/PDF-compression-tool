# -*- coding: utf-8 -*-
"""主窗口模块 - 应用现代样式"""
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("gui.main_window")
from typing import Optional
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QFileDialog,
    QApplication,
    QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from .widgets import FileDropEdit, FileInfoWidget, ProgressWidget, SettingsWidget, ResultWidget
from .styles import COLORS, get_app_style, BUTTON_PRIMARY, BUTTON_SECONDARY, BUTTON_DANGER, TITLE_STYLE
from ..core.compressor import PDFCompressor, CompressionResult
from ..core.analyzer import PDFAnalyzer
from ..utils.file_utils import validate_pdf, open_file_with_default_app, open_file_in_explorer, open_directory
from ..utils.config import load_config


class AnalysisWorker(QThread):
    finished = pyqtSignal(str, object)  # file_path, result_or_exception

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            analyzer = PDFAnalyzer()
            info = analyzer.quick_check(self.file_path)
            self.finished.emit(self.file_path, info)
        except Exception as e:
            self.finished.emit(self.file_path, e)


class CompressionWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(object)

    def __init__(self, input_path: str, target_size_mb: float, quality: int,
                 compression_mode: str = 'fast', backend: str = 'auto', ghostscript_path: str = '',
                 output_suffix: str = '_compressed', split_enabled: bool = True, parent=None):
        super().__init__(parent)
        self.input_path = input_path
        self.target_size_mb = target_size_mb
        self.quality = quality
        self.compression_mode = compression_mode
        self.backend = backend
        self.ghostscript_path = ghostscript_path
        self.output_suffix = output_suffix
        self.split_enabled = split_enabled
        self._is_cancelled = False

    def run(self):
        try:
            compressor = PDFCompressor(
                target_size_mb=self.target_size_mb,
                quality=self.quality,
                progress_callback=self._on_progress,
                compression_mode=self.compression_mode,
                backend=self.backend,
                ghostscript_path=self.ghostscript_path or None,
                output_suffix=self.output_suffix,
                split_enabled=self.split_enabled,
            )
            result = compressor.compress(self.input_path)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(CompressionResult(False, 0, 0, [], False, f"压缩失败: {str(e)}"))

    def _on_progress(self, value: int, message: str):
        if not self._is_cancelled:
            self.progress_updated.emit(value, message)

    def cancel(self):
        self._is_cancelled = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.worker: Optional[CompressionWorker] = None
        self._analysis_worker: Optional[AnalysisWorker] = None
        self.current_file: Optional[str] = None
        self.last_output_dir: Optional[str] = None
        self.last_output_files: Optional[list] = None
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("PDF压缩工具")
        self.setMinimumSize(650, 600)
        self.resize(750, 680)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLORS['background']}; }}")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(28, 24, 28, 24)

        self._create_title_area(main_layout)
        self._create_file_selection_area(main_layout)
        self.file_info_widget = FileInfoWidget()
        main_layout.addWidget(self.file_info_widget)
        self.settings_widget = SettingsWidget()
        self.settings_widget.set_defaults(
            target_size=int(self.config.target_size_mb),
            quality=int(self.config.default_quality),
            mode=self.config.compression_mode,
            backend=self.config.compression_backend
        )
        main_layout.addWidget(self.settings_widget)
        self.progress_widget = ProgressWidget()
        main_layout.addWidget(self.progress_widget)
        self.result_widget = ResultWidget()
        main_layout.addWidget(self.result_widget)
        self._create_button_area(main_layout)
        main_layout.addStretch()
        self._create_status_bar()

    def _create_title_area(self, parent_layout):
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 8)
        title_layout.setSpacing(4)
        title_label = QLabel("PDF 文件压缩工具")
        title_label.setStyleSheet(TITLE_STYLE)
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)
        subtitle_label = QLabel("智能压缩 · 保持清晰 · 自动分段")
        subtitle_label.setStyleSheet(f"QLabel {{ font-size: 13px; color: {COLORS['text_secondary']}; }}")
        subtitle_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(subtitle_label)
        parent_layout.addWidget(title_container)

    def _create_file_selection_area(self, parent_layout):
        file_container = QWidget()
        file_container.setStyleSheet(f"QWidget {{ background-color: {COLORS['surface']}; border: 1px solid {COLORS['border']}; border-radius: 12px; padding: 4px; }}")
        file_layout = QHBoxLayout(file_container)
        file_layout.setContentsMargins(12, 8, 12, 8)
        file_layout.setSpacing(10)
        self.file_edit = FileDropEdit()
        self.file_edit.setMinimumHeight(48)
        file_layout.addWidget(self.file_edit, stretch=1)
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setMinimumWidth(90)
        self.browse_btn.setMinimumHeight(48)
        self.browse_btn.setStyleSheet(BUTTON_SECONDARY)
        file_layout.addWidget(self.browse_btn)
        parent_layout.addWidget(file_container)

    def _create_button_area(self, parent_layout):
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 8, 0, 0)
        button_layout.setSpacing(12)
        self.start_btn = QPushButton("开始压缩")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setStyleSheet(BUTTON_PRIMARY)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        button_layout.addWidget(self.start_btn, stretch=2)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(48)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet(BUTTON_DANGER)
        button_layout.addWidget(self.cancel_btn, stretch=1)
        self.open_dir_btn = QPushButton("打开目录")
        self.open_dir_btn.setMinimumHeight(48)
        self.open_dir_btn.setEnabled(False)
        self.open_dir_btn.setStyleSheet(BUTTON_SECONDARY)
        button_layout.addWidget(self.open_dir_btn, stretch=1)
        parent_layout.addWidget(button_container)

    def _create_status_bar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.setStyleSheet(f"QStatusBar {{ font-size: 12px; color: {COLORS['text_secondary']}; background-color: {COLORS['surface']}; border-top: 1px solid {COLORS['border']}; padding: 6px 12px; min-height: 28px; }}")
        status_bar.showMessage("就绪 - 选择PDF文件开始压缩")

    def _connect_signals(self):
        self.browse_btn.clicked.connect(self._on_browse)
        self.file_edit.file_dropped.connect(self._on_file_selected)
        self.start_btn.clicked.connect(self._on_start)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.open_dir_btn.clicked.connect(self._on_open_output_dir)

    def _on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择PDF文件", "", "PDF文件 (*.pdf);;所有文件 (*.*)")
        if file_path:
            self._on_file_selected(file_path)

    def _on_file_selected(self, file_path: str):
        if not validate_pdf(file_path):
            QMessageBox.warning(self, "无效文件", "请选择有效的PDF文件")
            return
        self.file_edit.setText(file_path)
        self.current_file = file_path
        self.file_info_widget.update_info(0, 0, 0)
        self.statusBar().showMessage(f"正在分析: {Path(file_path).name}...")
        self.start_btn.setEnabled(False)
        if self._analysis_worker and self._analysis_worker.isRunning():
            self._analysis_worker.finished.disconnect(self._on_analysis_finished)
            self._analysis_worker.quit()
            self._analysis_worker.wait(1000)
        self._analysis_worker = AnalysisWorker(file_path)
        self._analysis_worker.finished.connect(self._on_analysis_finished)
        self._analysis_worker.start()

    def _on_analysis_finished(self, file_path: str, result):
        self._analysis_worker = None
        self.start_btn.setEnabled(True)
        if file_path != self.current_file:
            return
        if isinstance(result, Exception):
            QMessageBox.warning(self, "文件错误", f"无法读取文件: {str(result)}")
            self.statusBar().showMessage("分析失败")
            return
        self.file_info_widget.update_info(result['file_size_mb'], result['page_count'], 0)
        target_size = self.settings_widget.get_target_size()
        if result['file_size_mb'] <= target_size:
            self.result_widget.show_no_need(result['file_size_mb'], target_size)
        else:
            self.result_widget.clear()
        self.open_dir_btn.setEnabled(False)
        self.statusBar().showMessage(f"已加载: {Path(file_path).name}")

    def _on_start(self):
        file_path = self.file_edit.text()
        if not file_path:
            QMessageBox.warning(self, "提示", "请先选择PDF文件")
            return
        if not validate_pdf(file_path):
            QMessageBox.warning(self, "错误", "选择的文件不是有效的PDF")
            return

        target_size = self.settings_widget.get_target_size()
        quality = self.settings_widget.get_quality()
        compression_mode = self.settings_widget.get_compression_mode()
        backend = self.settings_widget.get_backend()

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.open_dir_btn.setEnabled(False)
        self.result_widget.clear()
        self.progress_widget.reset()

        self.config.set('split.enabled', self.settings_widget.is_auto_split_enabled())
        self.config.set('output.keep_original', self.settings_widget.is_keep_original())

        self.worker = CompressionWorker(
            file_path,
            target_size,
            quality,
            compression_mode=compression_mode,
            backend=backend,
            ghostscript_path=self.config.ghostscript_path,
            output_suffix=self.config.output_suffix,
            split_enabled=self.settings_widget.is_auto_split_enabled(),
        )
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.finished.connect(self._on_compression_finished)
        self.worker.start()
        self.statusBar().showMessage("正在压缩...")

    def _on_cancel(self):
        if self.worker:
            self.worker.cancel()
            self.worker.quit()
            if not self.worker.wait(5000):
                logger.warning("压缩线程未能在 5 秒内停止")
            self.worker = None
        self._reset_ui_state()
        self.statusBar().showMessage("已取消")
        self.progress_widget.set_progress(0, "已取消")

    def _on_progress_updated(self, value: int, message: str):
        self.progress_widget.set_progress(value, message)
        self.statusBar().showMessage(message)

    def _on_compression_finished(self, result: CompressionResult):
        self._reset_ui_state()
        if result.success:
            self.result_widget.show_success(result.original_size_mb, result.final_size_mb, result.output_files, result.was_split)
            self.open_dir_btn.setEnabled(True)
            self.statusBar().showMessage("压缩完成!")
            if result.output_files:
                self.last_output_dir = str(Path(result.output_files[0]).parent)
                self.last_output_files = result.output_files
            self._auto_open_result(result)
        else:
            self.result_widget.show_error(result.message)
            self.statusBar().showMessage("压缩失败")

    def _auto_open_result(self, result: CompressionResult):
        if not result.output_files:
            return
        try:
            if len(result.output_files) == 1:
                output_file = result.output_files[0]
                success = open_file_with_default_app(output_file)
                if not success:
                    open_file_in_explorer(output_file)
            else:
                open_file_in_explorer(result.output_files[0])
        except Exception as e:
            self.statusBar().showMessage(f"无法自动打开结果: {e}")

    def _on_open_output_dir(self):
        if self.last_output_files:
            open_file_in_explorer(self.last_output_files[0])
        elif self.last_output_dir:
            directory = self.last_output_dir
            if Path(directory).exists():
                open_directory(directory)
        else:
            file_path = self.file_edit.text()
            if file_path:
                open_file_in_explorer(file_path)

    def _reset_ui_state(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(self, "确认退出", "压缩正在进行中，确定要退出吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.worker.cancel()
                self.worker.quit()
                if not self.worker.wait(5000):
                    self.worker.terminate()
                    self.worker.wait(1000)
                event.accept()
            else:
                event.ignore()
        else:
            if self._analysis_worker and self._analysis_worker.isRunning():
                self._analysis_worker.quit()
                self._analysis_worker.wait(3000)
            event.accept()


def run_app():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(get_app_style())
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
