# -*- coding: utf-8 -*-
"""PDF压缩器核心模块 - 精确控制输出大小"""
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import fitz  # PyMuPDF

from .analyzer import PDFAnalyzer, PDFInfo
from ..utils.config import get_config
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
    SIZE_TOLERANCE = 0.05
    MIN_QUALITY = 30
    MAX_QUALITY = 95
    MIN_DPI = 50
    MAX_DPI = 200
    MAX_WORKERS = None
    GS_TIMEOUT = 300000

    def __init__(
        self,
        target_size_mb: Optional[float] = None,
        quality: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        force_compress: bool = False,
        size_tolerance: float = 0.05,
        use_multithreading: bool = True,
        compression_mode: str = "fast",
        backend: str = "auto",
        ghostscript_path: Optional[str] = None
    ):
        self.config = get_config()
        self.target_size_mb = target_size_mb or self.config.target_size_mb
        self.initial_quality = quality or self.config.default_quality
        self.min_quality = self.MIN_QUALITY
        self.force_compress = force_compress
        self.size_tolerance = size_tolerance
        self.use_multithreading = use_multithreading
        self.compression_mode = compression_mode
        self.backend = backend
        self.ghostscript_path = ghostscript_path

        self.analyzer = PDFAnalyzer()
        self.progress = CompressionProgress(progress_callback)
        self.logger = CompressionLogger(setup_logger("pdf_compressor"))

        self._progress_lock = Lock()
        self._pages_processed = 0
        self._total_pages = 0

    @property
    def max_render_iterations(self) -> int:
        if self.compression_mode == "fast":
            return 1
        if self.compression_mode == "balanced":
            return 2
        return 3

    def compress(self, input_path: str, output_path: Optional[str] = None) -> CompressionResult:
        original_size_mb = get_file_size_mb(input_path)
        if output_path is None:
            output_path = get_unique_output_path(input_path, self.config.output_suffix)

        self.logger.start_compression(input_path, original_size_mb)
        self.progress.update(0, "分析文件...", CompressionStage.ANALYSIS.value)

        target_min = self.target_size_mb * (1 - self.size_tolerance)
        if not self.force_compress and original_size_mb <= target_min:
            return CompressionResult(True, original_size_mb, original_size_mb, [input_path], False,
                                     f"文件已小于目标大小 {self.target_size_mb:.1f}MB，无需压缩")

        try:
            pdf_info = self.analyzer.analyze(input_path)
            gs_result = self._try_ghostscript_compress(input_path, output_path, pdf_info)
            if gs_result is not None:
                return self._create_result(original_size_mb, output_path, self.initial_quality, 120, False)

            self.progress.update(10, "执行轻量级压缩...", CompressionStage.LIGHTWEIGHT.value)
            current_path = self._stage1_lightweight_compress(input_path)
            current_size = get_file_size_mb(current_path)

            if current_size <= target_min and not self.force_compress:
                os.replace(current_path, output_path)
                return self._create_result(original_size_mb, output_path, 85, 96, False)

            if self._should_skip_image_rerender(pdf_info, current_size):
                self.logger.logger.info("检测为文本/矢量型PDF，跳过整页图像重渲染以提升速度")
                if current_path != input_path and os.path.exists(current_path):
                    os.replace(current_path, output_path)
                return self._create_result(original_size_mb, output_path, 85, 96, False)

            if current_size > self.target_size_mb:
                self.progress.update(30, "计算最优压缩参数...", CompressionStage.IMAGE_COMPRESS.value)
                new_path, new_size, final_quality, final_dpi = self._smart_image_compress(current_path, pdf_info)
                if new_size < current_size:
                    self._cleanup_temp(current_path)
                    current_path = new_path
                    current_size = new_size
                else:
                    self._cleanup_temp(new_path)
                    final_quality = 85
                    final_dpi = 96
            else:
                final_quality = 85
                final_dpi = 96

            if current_size > self.target_size_mb and self.config.split_enabled:
                self.progress.update(90, "执行分段处理...", CompressionStage.SPLIT.value)
                from .splitter import PDFSplitter
                splitter = PDFSplitter(self.target_size_mb)
                output_files = splitter.split(current_path, output_path)
                total_size = sum(get_file_size_mb(f) for f in output_files)
                self._cleanup_temp(current_path)
                return CompressionResult(True, original_size_mb, total_size, output_files, True,
                                         f"文件已分段为 {len(output_files)} 个部分",
                                         final_quality=final_quality, final_dpi=final_dpi)

            if current_path != input_path and os.path.exists(current_path):
                os.replace(current_path, output_path)
            elif os.path.exists(input_path):
                shutil.copy2(input_path, output_path)
            return self._create_result(original_size_mb, output_path, final_quality, final_dpi, False)

        except Exception as e:
            self.logger.log_error(e, "压缩过程")
            if 'current_path' in dir() and current_path and current_path != input_path:
                self._cleanup_temp(current_path)
            return CompressionResult(False, original_size_mb, 0, [], False, f"压缩失败: {str(e)}")

    def _should_try_ghostscript(self, pdf_info: PDFInfo) -> bool:
        if self.backend == "python":
            return False
        if self.backend == "ghostscript":
            return True
        if self.compression_mode == "fast":
            return True
        if not pdf_info.pages:
            return False
        image_pages = sum(1 for p in pdf_info.pages if p.image_count > 0)
        return (image_pages / len(pdf_info.pages)) >= 0.3

    def _resolve_ghostscript(self) -> Optional[str]:
        candidates = []
        if self.ghostscript_path:
            candidates.append(self.ghostscript_path)
        for name in ["gswin64c.exe", "gswin32c.exe", "gs"]:
            found = shutil.which(name)
            if found:
                candidates.append(found)
        for candidate in candidates:
            try:
                if not candidate:
                    continue
                path = str(Path(candidate))
                result = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10, shell=False)
                if result.returncode == 0 and result.stdout.strip():
                    self.logger.logger.info(f"检测到 Ghostscript: {path} ({result.stdout.strip()})")
                    return path
            except Exception:
                continue
        return None

    def _estimate_gs_profile(self, pdf_info: PDFInfo) -> dict:
        page_count = len(pdf_info.pages) if pdf_info.pages else 0
        image_pages = sum(1 for p in pdf_info.pages if p.image_count > 0) if pdf_info.pages else 0
        image_ratio = (image_pages / page_count) if page_count else 0
        target_ratio = self.target_size_mb / pdf_info.file_size_mb if pdf_info.file_size_mb else 1

        if self.compression_mode == "fast":
            profile = {
                'pdfsettings': '/screen',
                'dpi': 96 if target_ratio < 0.9 else 110,
                'jpeg_q': 40,
            }
        elif self.compression_mode == "balanced":
            profile = {
                'pdfsettings': '/ebook',
                'dpi': 120 if image_ratio > 0.5 else 135,
                'jpeg_q': 55,
            }
        else:
            profile = {
                'pdfsettings': '/printer',
                'dpi': 150 if image_ratio > 0.5 else 170,
                'jpeg_q': 70,
            }

        if target_ratio <= 0.75:
            profile['dpi'] = max(72, profile['dpi'] - 10)
            profile['jpeg_q'] = max(30, profile['jpeg_q'] - 5)
        elif target_ratio >= 0.95:
            profile['dpi'] = min(180, profile['dpi'] + 10)
            profile['jpeg_q'] = min(80, profile['jpeg_q'] + 5)

        return profile

    def _build_gs_command(self, gs_path: str, input_path: str, temp_output: str, profile: dict) -> List[str]:
        dpi = profile['dpi']
        jpeg_q = profile['jpeg_q']
        pdfsettings = profile['pdfsettings']
        return [
            gs_path,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-dPDFSETTINGS={pdfsettings}",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
            "-dAutoRotatePages=/None",
            "-dColorImageDownsampleType=/Bicubic",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dMonoImageDownsampleType=/Subsample",
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            f"-dColorImageResolution={dpi}",
            f"-dGrayImageResolution={dpi}",
            f"-dMonoImageResolution={max(150, dpi)}",
            "-dEncodeColorImages=true",
            "-dEncodeGrayImages=true",
            "-dEncodeMonoImages=true",
            f"-dJPEGQ={jpeg_q}",
            f"-sOutputFile={temp_output}",
            input_path,
        ]

    def _try_ghostscript_compress(self, input_path: str, output_path: str, pdf_info: PDFInfo) -> Optional[str]:
        if not self._should_try_ghostscript(pdf_info):
            return None

        gs_path = self._resolve_ghostscript()
        if not gs_path:
            self.logger.logger.info("Ghostscript 不可用，回退 Python 压缩流程")
            return None

        temp_output = str(Path(output_path).with_name(Path(output_path).stem + "_gs_temp.pdf"))
        profile = self._estimate_gs_profile(pdf_info)
        cmd = self._build_gs_command(gs_path, input_path, temp_output, profile)

        try:
            self.progress.update(5, f"尝试 Ghostscript 快速压缩... (DPI={profile['dpi']}, Q={profile['jpeg_q']})", CompressionStage.LIGHTWEIGHT.value)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.GS_TIMEOUT, shell=False)
            if result.returncode != 0:
                self.logger.logger.warning(f"Ghostscript 失败，回退 Python 流程: {result.stderr[:500]}")
                self._cleanup_temp(temp_output)
                return None
            if not os.path.exists(temp_output):
                self.logger.logger.warning("Ghostscript 未生成输出文件，回退 Python 流程")
                return None
            if not self._validate_pdf_output(temp_output, input_path):
                self.logger.logger.warning("Ghostscript 输出验证失败，回退 Python 流程")
                self._cleanup_temp(temp_output)
                return None

            temp_size = get_file_size_mb(temp_output)
            input_size = get_file_size_mb(input_path)
            reduction_ratio = 1 - (temp_size / input_size) if input_size > 0 else 0

            min_expected_reduction = 0.01 if self.compression_mode == 'fast' else 0.03
            if temp_size >= input_size * 1.02:
                self.logger.logger.warning("Ghostscript 输出更大，回退 Python 流程")
                self._cleanup_temp(temp_output)
                return None
            if self.backend == 'auto' and reduction_ratio < min_expected_reduction:
                self.logger.logger.info(f"Ghostscript 压缩收益过低({reduction_ratio*100:.1f}%)，回退 Python 流程")
                self._cleanup_temp(temp_output)
                return None

            os.replace(temp_output, output_path)
            self.logger.logger.info(
                f"Ghostscript 压缩成功，backend=ghostscript, size={temp_size:.2f}MB, "
                f"reduction={reduction_ratio*100:.1f}%, dpi={profile['dpi']}, q={profile['jpeg_q']}"
            )
            return output_path
        except Exception as e:
            self.logger.logger.warning(f"Ghostscript 异常，回退 Python 流程: {e}")
            self._cleanup_temp(temp_output)
            return None

    def _validate_pdf_output(self, output_path: str, input_path: str) -> bool:
        try:
            out_doc = fitz.open(output_path)
            in_doc = fitz.open(input_path)
            try:
                return len(out_doc) > 0 and len(out_doc) == len(in_doc)
            finally:
                out_doc.close()
                in_doc.close()
        except Exception:
            return False

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

    def _smart_image_compress(self, input_path: str, pdf_info: PDFInfo) -> Tuple[str, float, int, int]:
        target_max = self.target_size_mb
        target_min = self.target_size_mb * (1 - self.size_tolerance)
        initial_quality, initial_dpi = self._smart_estimate_initial_params(pdf_info, self.target_size_mb)
        best_path = input_path
        best_size = get_file_size_mb(input_path)
        best_quality = initial_quality
        best_dpi = initial_dpi
        quality_low, quality_high = self.MIN_QUALITY, self.MAX_QUALITY
        dpi_low, dpi_high = self.MIN_DPI, self.MAX_DPI
        current_path, current_size = self._render_with_params(input_path, initial_quality, initial_dpi, 0, pdf_info.pages)
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
        while iteration < self.max_render_iterations:
            iteration += 1
            progress = 30 + iteration * 15
            if best_size < target_min:
                new_quality = min((quality_low + quality_high) // 2 + 8, self.MAX_QUALITY)
                new_dpi = min((dpi_low + dpi_high) // 2 + 10, self.MAX_DPI)
                quality_low = new_quality
                dpi_low = new_dpi
            elif best_size > target_max:
                new_quality = max((quality_low + quality_high) // 2 - 8, self.MIN_QUALITY)
                new_dpi = max((dpi_low + dpi_high) // 2 - 10, self.MIN_DPI)
                quality_high = new_quality
                dpi_high = new_dpi
            else:
                break
            self.progress.update(progress, f"调整参数 (Q={new_quality}, DPI={new_dpi})...", CompressionStage.FINE_TUNING.value)
            current_path, current_size = self._render_with_params(input_path, new_quality, new_dpi, iteration, pdf_info.pages)
            if target_min <= current_size <= target_max:
                self._cleanup_temp(best_path)
                return current_path, current_size, new_quality, new_dpi
            if abs(current_size - self.target_size_mb) < abs(best_size - self.target_size_mb):
                self._cleanup_temp(best_path)
                best_path, best_size, best_quality, best_dpi = current_path, current_size, new_quality, new_dpi
            else:
                self._cleanup_temp(current_path)
        return best_path, best_size, best_quality, best_dpi

    def _smart_estimate_initial_params(self, pdf_info: PDFInfo, target_size_mb: float) -> Tuple[int, int]:
        original_size = pdf_info.file_size_mb
        target_ratio = target_size_mb / original_size if original_size > 0 else 0.5
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
        except Exception:
            return page_num, 595, 842, b"", default_dpi, False
        finally:
            doc.close()

    def _render_with_params(self, input_path: str, quality: int, dpi: int, iteration: int, pages=None) -> Tuple[str, float]:
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
            return self._render_multithreaded(input_path, output_path, quality, dpi, total_pages, pages)
        return self._render_single_threaded(input_path, output_path, quality, dpi, total_pages, pages)

    def _render_multithreaded(self, input_path: str, output_path: str, quality: int, dpi: int, total_pages: int, pages=None) -> Tuple[str, float]:
        new_doc = fitz.open()
        results = [None] * total_pages
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            page_info_list = pages if pages else [None] * total_pages
            futures = {executor.submit(self._render_page_worker, input_path, page_num, quality, dpi, page_info_list[page_num] if page_num < len(page_info_list) else None): page_num for page_num in range(total_pages)}
            for future in as_completed(futures):
                page_num, width, height, img_data, page_dpi, success = future.result()
                results[page_num] = (width, height, img_data, page_dpi, success)
                with self._progress_lock:
                    self._pages_processed += 1
                    progress_pct = int((self._pages_processed / self._total_pages) * 100)
                    if self.progress.callback:
                        self.progress.callback(30 + int(progress_pct * 0.6), f"处理页面 {self._pages_processed}/{self._total_pages} (DPI={page_dpi})")
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

    def _render_single_threaded(self, input_path: str, output_path: str, quality: int, dpi: int, total_pages: int, pages=None) -> Tuple[str, float]:
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
                if self.progress.callback:
                    self.progress.callback(30 + int(progress_pct * 0.6), f"处理页面 {self._pages_processed}/{total_pages} (DPI={page_dpi})")
            new_doc.save(output_path, garbage=4, deflate=True)
        finally:
            new_doc.close()
            doc.close()
        return output_path, get_file_size_mb(output_path)

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
            except Exception:
                pass

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
    ghostscript_path: Optional[str] = None
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
        ghostscript_path=ghostscript_path
    )
    return compressor.compress(input_path, output_path)
