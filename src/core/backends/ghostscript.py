"""Ghostscript 压缩后端"""
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

import fitz

from .base import CompressionBackend, BackendResult
from ..analyzer import PDFInfo
from ...utils.file_utils import get_file_size_mb

logger = logging.getLogger("backend.ghostscript")

GS_TIMEOUT = 300000


class GhostscriptBackend(CompressionBackend):

    def __init__(
        self,
        compression_mode: str = 'fast',
        target_size_mb: float = 200,
        ghostscript_path: Optional[str] = None,
    ):
        self.compression_mode = compression_mode
        self.target_size_mb = target_size_mb
        self.ghostscript_path = ghostscript_path

    def is_available(self) -> bool:
        return self._resolve_ghostscript() is not None

    def should_try(self, pdf_info: PDFInfo, backend: str) -> bool:
        if backend == "python":
            return False
        if backend == "ghostscript":
            return True
        if self.compression_mode == "fast":
            return True
        if not pdf_info.pages:
            return False
        image_pages = sum(1 for p in pdf_info.pages if p.image_count > 0)
        return (image_pages / len(pdf_info.pages)) >= 0.3

    def compress(
        self,
        input_path: str,
        output_path: str,
        pdf_info: PDFInfo,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> BackendResult:
        gs_path = self._resolve_ghostscript()
        if not gs_path:
            return BackendResult(None, False, message='Ghostscript 不可用')

        temp_output = str(Path(output_path).with_name(Path(output_path).stem + "_gs_temp.pdf"))
        profile = self._estimate_gs_profile(pdf_info)
        cmd = self._build_gs_command(gs_path, input_path, temp_output, profile)

        try:
            if progress_callback:
                progress_callback(5, f"尝试 Ghostscript 快速压缩... (DPI={profile['dpi']}, Q={profile['jpeg_q']})")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=GS_TIMEOUT, shell=False)
            if result.returncode != 0:
                logger.warning(f"Ghostscript 失败: {result.stderr[:500]}")
                self._cleanup_temp(temp_output)
                return BackendResult(None, False, message='Ghostscript 执行失败')

            if not os.path.exists(temp_output):
                logger.warning("Ghostscript 未生成输出文件")
                return BackendResult(None, False, message='Ghostscript 未生成输出文件')

            if not self._validate_pdf_output(temp_output, input_path):
                logger.warning("Ghostscript 输出验证失败")
                self._cleanup_temp(temp_output)
                return BackendResult(None, False, message='Ghostscript 输出验证失败')

            temp_size = get_file_size_mb(temp_output)
            input_size = get_file_size_mb(input_path)
            reduction_ratio = 1 - (temp_size / input_size) if input_size > 0 else 0

            min_expected_reduction = 0.01 if self.compression_mode == 'fast' else 0.03
            if temp_size >= input_size * 1.02:
                logger.warning("Ghostscript 输出更大，回退")
                self._cleanup_temp(temp_output)
                return BackendResult(None, False, message='Ghostscript 输出更大')
            if reduction_ratio < min_expected_reduction:
                logger.info(f"Ghostscript 压缩收益过低({reduction_ratio*100:.1f}%)，回退")
                self._cleanup_temp(temp_output)
                return BackendResult(None, False, message='Ghostscript 压缩收益过低')

            os.replace(temp_output, output_path)
            logger.info(
                f"Ghostscript 压缩成功, size={temp_size:.2f}MB, "
                f"reduction={reduction_ratio*100:.1f}%, dpi={profile['dpi']}, q={profile['jpeg_q']}"
            )
            return BackendResult(output_path, True, temp_size)

        except Exception as e:
            logger.warning(f"Ghostscript 异常: {e}")
            self._cleanup_temp(temp_output)
            return BackendResult(None, False, message=f'Ghostscript 异常: {e}')

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
                    logger.info(f"检测到 Ghostscript: {path} ({result.stdout.strip()})")
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
            profile = {'pdfsettings': '/screen', 'dpi': 96 if target_ratio < 0.9 else 110, 'jpeg_q': 40}
        elif self.compression_mode == "balanced":
            profile = {'pdfsettings': '/ebook', 'dpi': 120 if image_ratio > 0.5 else 135, 'jpeg_q': 55}
        else:
            profile = {'pdfsettings': '/printer', 'dpi': 150 if image_ratio > 0.5 else 170, 'jpeg_q': 70}

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
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-dPDFSETTINGS={pdfsettings}",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true", "-dSubsetFonts=true",
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

    def _cleanup_temp(self, temp_path: str):
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
