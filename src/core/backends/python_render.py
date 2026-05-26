"""Python 渲染压缩后端（基于 PyMuPDF）"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Callable, List, Optional, Tuple

import fitz

from .base import CompressionBackend, BackendResult
from ..analyzer import PDFInfo, PageInfo
from ...utils.file_utils import get_file_size_mb

logger = logging.getLogger("backend.python_render")


class PythonRenderBackend(CompressionBackend):

    def __init__(
        self,
        target_size_mb: float = 200,
        use_multithreading: bool = True,
    ):
        self.target_size_mb = target_size_mb
        self.use_multithreading = use_multithreading
        self._progress_lock = Lock()
        self._pages_processed = 0
        self._total_pages = 0

    def is_available(self) -> bool:
        return True

    def compress(
        self,
        input_path: str,
        output_path: str,
        pdf_info: PDFInfo,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> BackendResult:
        """不执行压缩，仅标记为可用。实际渲染由 optimizer 调用 render_with_params。"""
        return BackendResult(None, False, message='PythonRenderBackend 需要通过 render_with_params 调用')

    def render_with_params(
        self,
        input_path: str,
        quality: int,
        dpi: int,
        iteration: int,
        pages: Optional[List[PageInfo]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[str, float]:
        """
        用指定参数渲染 PDF 为图像 PDF。

        Returns:
            (output_path, output_size_mb)
        """
        total_pages = len(pages) if pages else 0
        if total_pages == 0:
            doc = fitz.open(input_path)
            try:
                total_pages = len(doc)
            finally:
                doc.close()

        p = Path(input_path)
        stem = p.stem.replace("_stage1_temp", "").replace("_stage2_temp", "")
        suffix = f"_stage2_temp.pdf" if iteration == 0 else f"_temp_{iteration}.pdf"
        output_path = str(p.parent / f"{stem}{suffix}")

        self._total_pages = total_pages
        self._pages_processed = 0

        if self.use_multithreading and total_pages > 1:
            return self._render_multithreaded(input_path, output_path, quality, dpi, total_pages, pages, progress_callback)
        return self._render_single_threaded(input_path, output_path, quality, dpi, total_pages, pages, progress_callback)

    def _render_page_worker(self, input_path: str, page_num: int, quality: int, default_dpi: int, page_info=None):
        doc = fitz.open(input_path)
        try:
            page = doc[page_num]
            rect = page.rect
            page_dpi = self._adaptive_dpi_for_page(page, default_dpi, page_info)
            page_matrix = fitz.Matrix(page_dpi / 72.0, page_dpi / 72.0)
            pix = page.get_pixmap(matrix=page_matrix, alpha=False)
            img_data = pix.tobytes("jpeg", jpg_quality=quality)
            return page_num, rect.width, rect.height, img_data, page_dpi, True
        except Exception as e:
            logger.warning(f"页面 {page_num} 渲染失败: {e}")
            return page_num, 595, 842, b"", default_dpi, False
        finally:
            doc.close()

    def _adaptive_dpi_for_page(self, page: fitz.Page, default_dpi: int, page_info=None) -> int:
        try:
            if page_info is not None:
                text_length = page_info.text_length
                image_count = page_info.image_count
            else:
                text = page.get_text()
                text_length = len(text.strip())
                image_count = len(page.get_images(full=False))
            if image_count == 0 and text_length > 100:
                return 72
            if image_count > 2:
                return default_dpi
            if image_count > 0 and text_length > 50:
                return min(96, default_dpi)
            return default_dpi
        except Exception:
            return default_dpi

    def _render_multithreaded(self, input_path: str, output_path: str, quality: int, dpi: int,
                              total_pages: int, pages=None, progress_callback=None) -> Tuple[str, float]:
        new_doc = fitz.open()
        results = [None] * total_pages
        with ThreadPoolExecutor() as executor:
            page_info_list = pages if pages else [None] * total_pages
            futures = {
                executor.submit(self._render_page_worker, input_path, page_num, quality, dpi,
                                page_info_list[page_num] if page_num < len(page_info_list) else None): page_num
                for page_num in range(total_pages)
            }
            for future in as_completed(futures):
                page_num, width, height, img_data, page_dpi, success = future.result()
                results[page_num] = (width, height, img_data, page_dpi, success)
                with self._progress_lock:
                    self._pages_processed += 1
                    progress_pct = int((self._pages_processed / self._total_pages) * 100)
                    if progress_callback:
                        progress_callback(30 + int(progress_pct * 0.6), f"处理页面 {self._pages_processed}/{self._total_pages} (DPI={page_dpi})")

        for item in results:
            if not item:
                continue
            width, height, img_data, _, success = item
            if success and img_data:
                rect = fitz.Rect(0, 0, width, height)
                page = new_doc.new_page(width=width, height=height)
                page.insert_image(rect, stream=img_data)

        new_doc.save(output_path, garbage=4, deflate=True)
        new_doc.close()
        return output_path, get_file_size_mb(output_path)

    def _render_single_threaded(self, input_path: str, output_path: str, quality: int, dpi: int,
                                total_pages: int, pages=None, progress_callback=None) -> Tuple[str, float]:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        try:
            for page_num in range(total_pages):
                page = doc[page_num]
                rect = page.rect
                page_info = pages[page_num] if pages and page_num < len(pages) else None
                page_dpi = self._adaptive_dpi_for_page(page, dpi, page_info)
                page_matrix = fitz.Matrix(page_dpi / 72.0, page_dpi / 72.0)
                pix = page.get_pixmap(matrix=page_matrix, alpha=False)
                img_data = pix.tobytes("jpeg", jpg_quality=quality)
                new_page = new_doc.new_page(width=rect.width, height=rect.height)
                new_page.insert_image(rect, stream=img_data)
                self._pages_processed = page_num + 1
                progress_pct = int((self._pages_processed / total_pages) * 100)
                if progress_callback:
                    progress_callback(30 + int(progress_pct * 0.6), f"处理页面 {self._pages_processed}/{total_pages} (DPI={page_dpi})")
            new_doc.save(output_path, garbage=4, deflate=True)
        finally:
            new_doc.close()
            doc.close()
        return output_path, get_file_size_mb(output_path)
