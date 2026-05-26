"""优化器模块测试"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.analyzer import PDFInfo, PageInfo
from src.core.optimizer import CompressionOptimizer


def make_pdf_info(file_size_mb=100, page_count=10, image_pages=0, text_length=500):
    pages = []
    for i in range(page_count):
        img_count = 1 if i < image_pages else 0
        pages.append(PageInfo(i, 595, 842, img_count, text_length))
    return PDFInfo('test.pdf', file_size_mb, page_count, image_pages, True, False, [], pages)


class TestCompressionOptimizer:

    def test_max_iterations_fast(self):
        opt = CompressionOptimizer(200, compression_mode="fast")
        assert opt.max_iterations == 1

    def test_max_iterations_balanced(self):
        opt = CompressionOptimizer(200, compression_mode="balanced")
        assert opt.max_iterations == 2

    def test_max_iterations_high_quality(self):
        opt = CompressionOptimizer(200, compression_mode="high_quality")
        assert opt.max_iterations == 3

    def test_estimate_initial_params_high_ratio(self):
        opt = CompressionOptimizer(80)
        info = make_pdf_info(file_size_mb=100)
        quality, dpi = opt._estimate_initial_params(info)
        assert quality == 85
        assert dpi == 150

    def test_estimate_initial_params_medium_ratio_image_heavy(self):
        opt = CompressionOptimizer(50)
        info = make_pdf_info(file_size_mb=100, page_count=10, image_pages=8)
        quality, dpi = opt._estimate_initial_params(info)
        assert quality == 75
        assert dpi == 120

    def test_estimate_initial_params_medium_ratio_text_heavy(self):
        opt = CompressionOptimizer(50)
        info = make_pdf_info(file_size_mb=100, page_count=10, image_pages=0, text_length=600)
        quality, dpi = opt._estimate_initial_params(info)
        assert quality == 80
        assert dpi == 96

    def test_estimate_initial_params_low_ratio(self):
        opt = CompressionOptimizer(25)
        info = make_pdf_info(file_size_mb=100)
        quality, dpi = opt._estimate_initial_params(info)
        assert quality == 45
        assert dpi == 72

    def test_estimate_initial_params_very_low_ratio(self):
        opt = CompressionOptimizer(15)
        info = make_pdf_info(file_size_mb=100)
        quality, dpi = opt._estimate_initial_params(info)
        assert quality == 45
        assert dpi == 72
