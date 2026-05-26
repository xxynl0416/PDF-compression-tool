# -*- coding: utf-8 -*-
"""PDF压缩器 — 编排器：分析 → GS尝试 → 轻量压缩 → 图像压缩 → 分段"""
import os
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

import fitz

from .analyzer import PDFAnalyzer, PDFInfo
from .backends.ghostscript import GhostscriptBackend
from .backends.python_render import PythonRenderBackend
from .optimizer import CompressionOptimizer
from ..utils.file_utils import get_file_size_mb, get_unique_output_path
from ..utils.logger import CompressionLogger, setup_logger


class CompressionStage(Enum):
    ANALYSIS = "分析文件"
    LIGHTWEIGHT = "轻量压缩"
    IMAGE_COMPRESS = "图像压缩"
    FINE_TUNING = "精细调整"
    SPLIT = "分段处理"


@dataclass
class CompressionResult:
    success: bool
    original_size_mb: float
    final_size_mb: float
    output_files: List[str]
    was_split: bool
    message: str
    compression_ratio: float = 0.0
    final_quality: int = 85
    final_dpi: int = 96

    def __post_init__(self):
        if self.original_size_mb > 0:
            self.compression_ratio = self.final_size_mb / self.original_size_mb


class CompressionProgress:
    def __init__(self, callback: Optional[Callable[[int, str], None]] = None):
        self.callback = callback
        self.current_stage = ""
        self.progress = 0
        self.message = ""

    def update(self, progress: int, message: str, stage: str = ""):
        self.progress = progress
        self.message = message
        if stage:
            self.current_stage = stage
        if self.callback:
            self.callback(progress, message)


class PDFCompressor:
    """PDF 压缩编排器 — 协调后端、优化器和分段器"""

    def __init__(
        self,
        target_size_mb: float = 200,
        quality: int = 85,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        force_compress: bool = False,
        size_tolerance: float = 0.05,
        use_multithreading: bool = True,
        compression_mode: str = "fast",
        backend: str = "auto",
        ghostscript_path: Optional[str] = None,
        output_suffix: str = "_compressed",
        split_enabled: bool = True,
    ):
        self.target_size_mb = target_size_mb
        self.initial_quality = quality
        self.force_compress = force_compress
        self.size_tolerance = size_tolerance
        self.compression_mode = compression_mode
        self.backend = backend
        self.output_suffix = output_suffix
        self.split_enabled = split_enabled

        self.analyzer = PDFAnalyzer()
        self.progress = CompressionProgress(progress_callback)
        self.logger = CompressionLogger(setup_logger("pdf_compressor"))

        self._gs_backend = GhostscriptBackend(compression_mode, target_size_mb, ghostscript_path)
        self._py_backend = PythonRenderBackend(target_size_mb, use_multithreading)

    def compress(self, input_path: str, output_path: Optional[str] = None) -> CompressionResult:
        original_size_mb = get_file_size_mb(input_path)
        if output_path is None:
            output_path = get_unique_output_path(input_path, self.output_suffix)

        self.logger.start_compression(input_path, original_size_mb)
        self.progress.update(0, "分析文件...", CompressionStage.ANALYSIS.value)

        target_min = self.target_size_mb * (1 - self.size_tolerance)
        if not self.force_compress and original_size_mb <= target_min:
            return CompressionResult(True, original_size_mb, original_size_mb, [input_path], False,
                                     f"文件已小于目标大小 {self.target_size_mb:.1f}MB，无需压缩")

        current_path = None
        try:
            pdf_info = self.analyzer.analyze(input_path)

            # 1. 尝试 Ghostscript 快速压缩
            if self._gs_backend.should_try(pdf_info, self.backend):
                self.progress.update(5, "尝试 Ghostscript 快速压缩...", CompressionStage.LIGHTWEIGHT.value)
                gs_result = self._gs_backend.compress(input_path, output_path, pdf_info, self.progress.callback)
                if gs_result.success:
                    return self._create_result(original_size_mb, output_path, self.initial_quality, 120, False)

            # 2. 轻量压缩（清除元数据、清理内容流）
            self.progress.update(10, "执行轻量级压缩...", CompressionStage.LIGHTWEIGHT.value)
            current_path = self._stage1_lightweight_compress(input_path)
            current_size = get_file_size_mb(current_path)

            if current_size <= target_min and not self.force_compress:
                os.replace(current_path, output_path)
                return self._create_result(original_size_mb, output_path, 85, 96, False)

            # 3. 判断是否需要图像重渲染
            if self._should_skip_image_rerender(pdf_info, current_size):
                self.logger.logger.info("检测为文本/矢量型PDF，跳过整页图像重渲染以提升速度")
                if current_path != input_path and os.path.exists(current_path):
                    os.replace(current_path, output_path)
                return self._create_result(original_size_mb, output_path, 85, 96, False)

            # 4. 智能图像压缩（二分搜索最优参数）
            if current_size > self.target_size_mb:
                self.progress.update(30, "计算最优压缩参数...", CompressionStage.IMAGE_COMPRESS.value)
                optimizer = CompressionOptimizer(
                    self.target_size_mb, self.size_tolerance, self.compression_mode, self.progress.callback
                )
                new_path, new_size, final_quality, final_dpi = optimizer.find_best_params(
                    current_path, pdf_info, self._py_backend
                )
                if new_size < current_size:
                    self._cleanup_temp(current_path)
                    current_path = new_path
                    current_size = new_size
                else:
                    self._cleanup_temp(new_path)
                    final_quality, final_dpi = 85, 96
            else:
                final_quality, final_dpi = 85, 96

            # 5. 分段处理
            if current_size > self.target_size_mb and self.split_enabled:
                self.progress.update(90, "执行分段处理...", CompressionStage.SPLIT.value)
                from .splitter import PDFSplitter
                splitter = PDFSplitter(self.target_size_mb, segment_suffix="_part")
                output_files = splitter.split(current_path, output_path)
                total_size = sum(get_file_size_mb(f) for f in output_files)
                self._cleanup_temp(current_path)
                return CompressionResult(True, original_size_mb, total_size, output_files, True,
                                         f"文件已分段为 {len(output_files)} 个部分",
                                         final_quality=final_quality, final_dpi=final_dpi)

            # 6. 输出单文件
            if current_path != input_path and os.path.exists(current_path):
                os.replace(current_path, output_path)
            elif os.path.exists(input_path):
                shutil.copy2(input_path, output_path)
            return self._create_result(original_size_mb, output_path, final_quality, final_dpi, False)

        except Exception as e:
            self.logger.log_error(e, "压缩过程")
            if current_path is not None and current_path != input_path:
                self._cleanup_temp(current_path)
            return CompressionResult(False, original_size_mb, 0, [], False, f"压缩失败: {str(e)}")

    def _should_skip_image_rerender(self, pdf_info: PDFInfo, current_size: float) -> bool:
        if not pdf_info.pages:
            return False
        text_heavy_pages = sum(1 for p in pdf_info.pages if p.text_length > 200 and p.image_count == 0)
        image_heavy_pages = sum(1 for p in pdf_info.pages if p.image_count > 0)
        total_pages = len(pdf_info.pages)
        text_ratio = text_heavy_pages / total_pages if total_pages else 0
        image_ratio = image_heavy_pages / total_pages if total_pages else 0
        if self.compression_mode == "fast" and text_ratio >= 0.6:
            return True
        if current_size <= self.target_size_mb * 1.2 and text_ratio >= 0.6 and image_ratio <= 0.4:
            return True
        if text_ratio >= 0.8 and image_ratio <= 0.2:
            return True
        return False

    def _stage1_lightweight_compress(self, input_path: str) -> str:
        doc = fitz.open(input_path)
        p = Path(input_path)
        output_path = str(p.parent / f"{p.stem}_stage1_temp.pdf")
        try:
            doc.set_metadata({})
            for page in doc:
                page.clean_contents()
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            return output_path
        finally:
            doc.close()

    def _cleanup_temp(self, temp_path: str):
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                self.logger.logger.warning(f"清理临时文件失败 {temp_path}: {e}")

    def _create_result(self, original_size_mb: float, output_path: str, quality: int, dpi: int, was_split: bool) -> CompressionResult:
        final_size = get_file_size_mb(output_path)
        compression_percent = (1 - final_size / original_size_mb) * 100 if original_size_mb > 0 else 0
        target_min = self.target_size_mb * (1 - self.size_tolerance)
        if final_size <= self.target_size_mb and final_size >= target_min:
            status = "精确达标"
        elif final_size < target_min:
            status = "略小于目标（可提高画质）"
        else:
            status = "略大于目标"
        return CompressionResult(True, original_size_mb, final_size, [output_path], was_split,
                                 f"压缩完成，体积减少 {compression_percent:.1f}% ({status})",
                                 final_quality=quality, final_dpi=dpi)


def compress_pdf(
    input_path: str,
    output_path: Optional[str] = None,
    target_size_mb: float = 200,
    quality: int = 85,
    force_compress: bool = False,
    size_tolerance: float = 0.05,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    use_multithreading: bool = True,
    compression_mode: str = "fast",
    backend: str = "auto",
    ghostscript_path: Optional[str] = None,
    output_suffix: str = "_compressed",
    split_enabled: bool = True,
) -> CompressionResult:
    compressor = PDFCompressor(
        target_size_mb=target_size_mb,
        quality=quality,
        progress_callback=progress_callback,
        force_compress=force_compress,
        size_tolerance=size_tolerance,
        use_multithreading=use_multithreading,
        compression_mode=compression_mode,
        backend=backend,
        ghostscript_path=ghostscript_path,
        output_suffix=output_suffix,
        split_enabled=split_enabled,
    )
    return compressor.compress(input_path, output_path)
