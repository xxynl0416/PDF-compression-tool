# -*- coding: utf-8 -*-
"""PDFCompressor 编排器测试"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.compressor import PDFCompressor, CompressionResult
from src.core.analyzer import PDFInfo, PageInfo


def make_pdf_info(file_size_mb=100, page_count=10, image_pages=0, text_length=500):
    """构造 PDFInfo 测试对象。

    Args:
        file_size_mb: 模拟文件大小 (MB)
        page_count: 总页数
        image_pages: 含图片的页数 (前 N 页)
        text_length: 每页文本长度；>200 且 image_count==0 的页面被视为"文本页"
    """
    pages = []
    for i in range(page_count):
        img_count = 1 if i < image_pages else 0
        pages.append(PageInfo(i, 595, 842, img_count, text_length))
    return PDFInfo('test.pdf', file_size_mb, page_count, image_pages, True, False, [], pages)


# ---------------------------------------------------------------------------
# _should_skip_image_rerender 纯函数测试
# ---------------------------------------------------------------------------
class TestShouldSkipImageRerender:

    # -- fast 模式 ----------------------------------------------------------
    def test_fast_mode_text_heavy_should_skip(self):
        """fast 模式 + 80% 纯文本页 (text_length>200, no images) → True"""
        compressor = PDFCompressor(compression_mode="fast", target_size_mb=200)
        # 10 页中 8 页纯文本，0 页有图 → text_ratio=0.8 >= 0.6
        info = make_pdf_info(page_count=10, image_pages=0, text_length=500)
        assert compressor._should_skip_image_rerender(info, current_size=50.0) is True

    def test_fast_mode_low_text_ratio_should_not_skip(self):
        """fast 模式 + 30% 文本页 → False (text_ratio < 0.6)"""
        compressor = PDFCompressor(compression_mode="fast", target_size_mb=200)
        # 10 页中 7 页有图，3 页纯文本 → text_ratio=0.3
        info = make_pdf_info(page_count=10, image_pages=7, text_length=500)
        assert compressor._should_skip_image_rerender(info, current_size=50.0) is False

    # -- balanced 模式 ------------------------------------------------------
    def test_balanced_mode_text_heavy_small_size_should_skip(self):
        """balanced 模式 + text-heavy + 小尺寸 → True (第二条规则)"""
        compressor = PDFCompressor(compression_mode="balanced", target_size_mb=200)
        # 10 页中 8 页纯文本，0 页有图 → text_ratio=0.8, image_ratio=0.0
        # current_size=100 <= 200*1.2=240, text_ratio>=0.6, image_ratio<=0.4
        info = make_pdf_info(page_count=10, image_pages=0, text_length=500)
        assert compressor._should_skip_image_rerender(info, current_size=100.0) is True

    def test_balanced_mode_image_heavy_should_not_skip(self):
        """balanced 模式 + 图片密集 → False"""
        compressor = PDFCompressor(compression_mode="balanced", target_size_mb=200)
        # 10 页中 8 页有图 → image_ratio=0.8, text_ratio=0.2
        info = make_pdf_info(page_count=10, image_pages=8, text_length=500)
        assert compressor._should_skip_image_rerender(info, current_size=300.0) is False

    # -- text_ratio >= 0.8 通用规则 -----------------------------------------
    def test_high_text_ratio_should_skip_regardless_of_mode(self):
        """text_ratio>=0.8 + image_ratio<=0.2 → True（不限 compression_mode）"""
        compressor = PDFCompressor(compression_mode="balanced", target_size_mb=200)
        # 10 页中 1 页有图 → text_ratio=0.8（8 页 text_length>200 且无图）
        # image_ratio=0.1 <= 0.2
        info = make_pdf_info(page_count=10, image_pages=1, text_length=500)
        assert compressor._should_skip_image_rerender(info, current_size=300.0) is True

    # -- 边界情况 ------------------------------------------------------------
    def test_empty_pages_returns_false(self):
        """空页列表 → False"""
        compressor = PDFCompressor(compression_mode="fast", target_size_mb=200)
        info = make_pdf_info(page_count=0, image_pages=0, text_length=0)
        assert compressor._should_skip_image_rerender(info, current_size=10.0) is False

    def test_low_text_length_not_counted_as_text_page(self):
        """text_length <= 200 的页面不计入文本页"""
        compressor = PDFCompressor(compression_mode="fast", target_size_mb=200)
        # 10 页全部 text_length=100 (<=200) → text_ratio=0.0
        info = make_pdf_info(page_count=10, image_pages=0, text_length=100)
        assert compressor._should_skip_image_rerender(info, current_size=50.0) is False


# ---------------------------------------------------------------------------
# CompressionResult 计算测试
# ---------------------------------------------------------------------------
class TestCompressionResult:

    def test_compression_ratio_computed_correctly(self):
        """compression_ratio = final_size / original_size"""
        result = CompressionResult(
            success=True,
            original_size_mb=200.0,
            final_size_mb=100.0,
            output_files=["out.pdf"],
            was_split=False,
            message="ok",
        )
        assert result.compression_ratio == pytest.approx(0.5)

    def test_compression_ratio_zero_original(self):
        """original_size=0 时 compression_ratio 保持默认 0.0"""
        result = CompressionResult(
            success=True,
            original_size_mb=0.0,
            final_size_mb=0.0,
            output_files=[],
            was_split=False,
            message="ok",
        )
        assert result.compression_ratio == 0.0

    def test_compression_ratio_no_compression(self):
        """文件未变小时 ratio = 1.0"""
        result = CompressionResult(
            success=True,
            original_size_mb=50.0,
            final_size_mb=50.0,
            output_files=["out.pdf"],
            was_split=False,
            message="ok",
        )
        assert result.compression_ratio == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# force_compress 流程测试
# ---------------------------------------------------------------------------
class TestForceCompress:

    def test_force_compress_skips_size_check(self):
        """force_compress=True 时即使文件小于目标也进入压缩流程"""
        compressor = PDFCompressor(
            target_size_mb=200,
            force_compress=True,
            compression_mode="fast",
            backend="ghostscript",
        )

        # 模拟 analyzer 和后端，避免真实 I/O
        mock_info = make_pdf_info(file_size_mb=50, page_count=10, image_pages=0)

        with patch.object(compressor.analyzer, 'analyze', return_value=mock_info), \
             patch.object(compressor._gs_backend, 'should_try', return_value=False), \
             patch('src.core.compressor.get_file_size_mb', return_value=50.0), \
             patch.object(compressor, '_stage1_lightweight_compress', return_value='/tmp/out.pdf'), \
             patch.object(compressor, '_create_result') as mock_create:

            mock_create.return_value = CompressionResult(
                success=True, original_size_mb=50.0, final_size_mb=40.0,
                output_files=["out.pdf"], was_split=False, message="done",
            )
            compressor.compress("input.pdf", "output.pdf")

            # force_compress=True 时 analyzer.analyze 应被调用（进入压缩流程）
            compressor.analyzer.analyze.assert_called_once_with("input.pdf")

    def test_no_force_skips_when_below_target(self):
        """force_compress=False 且文件已小于目标时直接返回，不进入分析"""
        compressor = PDFCompressor(
            target_size_mb=200,
            force_compress=False,
            size_tolerance=0.05,
        )

        with patch('src.core.compressor.get_file_size_mb', return_value=50.0), \
             patch.object(compressor.analyzer, 'analyze') as mock_analyze:

            result = compressor.compress("input.pdf", "output.pdf")

            # 文件 50MB < 200*(1-0.05)=190MB，应直接返回，不调用 analyze
            mock_analyze.assert_not_called()
            assert result.success is True
            assert "无需压缩" in result.message
