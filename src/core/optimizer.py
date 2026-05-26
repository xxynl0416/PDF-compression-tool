"""压缩参数优化器 — 二分搜索逼近目标大小"""
import logging
import os
from typing import Callable, List, Optional, Tuple

from .analyzer import PDFInfo, PageInfo
from .backends.python_render import PythonRenderBackend
from ..utils.file_utils import get_file_size_mb

logger = logging.getLogger("optimizer")

MIN_QUALITY = 30
MAX_QUALITY = 95
MIN_DPI = 50
MAX_DPI = 200


class CompressionOptimizer:
    """通过二分搜索找到最优 quality/dpi 参数组合"""

    def __init__(
        self,
        target_size_mb: float,
        size_tolerance: float = 0.05,
        compression_mode: str = 'fast',
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ):
        self.target_size_mb = target_size_mb
        self.size_tolerance = size_tolerance
        self.compression_mode = compression_mode
        self.progress_callback = progress_callback

    @property
    def max_iterations(self) -> int:
        if self.compression_mode == "fast":
            return 1
        if self.compression_mode == "balanced":
            return 2
        return 3

    def find_best_params(
        self,
        input_path: str,
        pdf_info: PDFInfo,
        render_backend: PythonRenderBackend,
    ) -> Tuple[str, float, int, int]:
        """
        搜索最优压缩参数。

        Returns:
            (output_path, output_size_mb, final_quality, final_dpi)
        """
        target_max = self.target_size_mb
        target_min = self.target_size_mb * (1 - self.size_tolerance)
        initial_quality, initial_dpi = self._estimate_initial_params(pdf_info)

        best_path = input_path
        best_size = get_file_size_mb(input_path)
        best_quality = initial_quality
        best_dpi = initial_dpi

        quality_low, quality_high = MIN_QUALITY, MAX_QUALITY
        dpi_low, dpi_high = MIN_DPI, MAX_DPI

        current_path, current_size = render_backend.render_with_params(
            input_path, initial_quality, initial_dpi, 0, pdf_info.pages, self.progress_callback
        )

        if target_min <= current_size <= target_max:
            return current_path, current_size, initial_quality, initial_dpi

        if current_size < target_min:
            quality_low = initial_quality
            dpi_low = initial_dpi
        else:
            quality_high = initial_quality
            dpi_high = initial_dpi

        best_path, best_size, best_quality, best_dpi = current_path, current_size, initial_quality, initial_dpi

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            progress = 30 + iteration * 15

            if best_size < target_min:
                new_quality = min((quality_low + quality_high) // 2, MAX_QUALITY)
                new_dpi = min((dpi_low + dpi_high) // 2, MAX_DPI)
                quality_low = new_quality
                dpi_low = new_dpi
            elif best_size > target_max:
                new_quality = max((quality_low + quality_high) // 2, MIN_QUALITY)
                new_dpi = max((dpi_low + dpi_high) // 2, MIN_DPI)
                quality_high = new_quality
                dpi_high = new_dpi
            else:
                break

            if self.progress_callback:
                self.progress_callback(progress, f"调整参数 (Q={new_quality}, DPI={new_dpi})...")

            current_path, current_size = render_backend.render_with_params(
                input_path, new_quality, new_dpi, iteration, pdf_info.pages, self.progress_callback
            )

            if target_min <= current_size <= target_max:
                self._cleanup_temp(best_path)
                return current_path, current_size, new_quality, new_dpi

            if abs(current_size - self.target_size_mb) < abs(best_size - self.target_size_mb):
                self._cleanup_temp(best_path)
                best_path, best_size, best_quality, best_dpi = current_path, current_size, new_quality, new_dpi
            else:
                self._cleanup_temp(current_path)

        return best_path, best_size, best_quality, best_dpi

    def _estimate_initial_params(self, pdf_info: PDFInfo) -> Tuple[int, int]:
        original_size = pdf_info.file_size_mb
        target_ratio = self.target_size_mb / original_size if original_size > 0 else 0.5
        page_count = len(pdf_info.pages)
        image_pages = sum(1 for p in pdf_info.pages if p.image_count > 0)
        text_heavy_pages = sum(1 for p in pdf_info.pages if p.text_length > 500)
        text_ratio = text_heavy_pages / page_count if page_count else 0
        image_ratio = image_pages / page_count if page_count else 0

        if target_ratio >= 0.8:
            quality, dpi = 85, 150
        elif target_ratio >= 0.5:
            if image_ratio > 0.7:
                quality, dpi = 75, 120
            elif text_ratio > 0.5:
                quality, dpi = 80, 96
            else:
                quality, dpi = 70, 100
        elif target_ratio >= 0.3:
            if image_ratio > 0.7:
                quality, dpi = 60, 96
            elif text_ratio > 0.5:
                quality, dpi = 70, 72
            else:
                quality, dpi = 55, 85
        else:
            quality, dpi = 45, 72
        return quality, dpi

    def _cleanup_temp(self, temp_path: str):
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
