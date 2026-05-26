# -*- coding: utf-8 -*-
"""PDFSplitter模块测试"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.splitter import PDFSplitter


class TestCalculateSplitPoints:
    """_calculate_split_points 纯函数测试"""

    def test_empty_page_sizes(self):
        """空页面列表应返回 [0]"""
        splitter = PDFSplitter()
        result = splitter._calculate_split_points([])
        assert result == [0]

    def test_single_page_under_target(self):
        """单页且未超过目标大小，返回 [0]"""
        splitter = PDFSplitter(max_size_mb=200)
        result = splitter._calculate_split_points([50.0])
        assert result == [0]

    def test_multiple_small_pages_fit_in_one_segment(self):
        """多页小文件，总大小在单段范围内，返回 [0]"""
        splitter = PDFSplitter(max_size_mb=200)
        # 5页 * 30MB = 150MB, target_size = 200 * 0.92 = 184MB
        page_sizes = [30.0] * 5
        result = splitter._calculate_split_points(page_sizes)
        assert result == [0]

    def test_multiple_pages_need_splitting(self):
        """多页文件需要分段，返回 [0, N]"""
        splitter = PDFSplitter(max_size_mb=10)
        # target_size = 10 * 0.92 = 9.2MB
        # Pages: [4, 4, 4] -> 前两页累积8MB <= 9.2, 第三页加入会到12MB > 9.2
        # 且 |8-9.2|=1.2 < |12-9.2|=2.8, 所以在index=2处分割
        page_sizes = [4.0, 4.0, 4.0]
        result = splitter._calculate_split_points(page_sizes)
        assert result[0] == 0
        assert len(result) == 2
        assert result[1] == 2

    def test_single_oversized_page(self):
        """单页超过限制，应获得独立分段"""
        splitter = PDFSplitter(max_size_mb=200)
        # 单页210MB > 200MB限制
        result = splitter._calculate_split_points([210.0])
        # 超大页自己成段: split_points = [0]，然后因为没有后续页面，不追加额外点
        # 但逻辑中 current_size=0 且 size > target_max:
        #   current_size > 0 为 False, 跳过
        #   i+1 < len(page_sizes) 为 False, 跳过
        assert result == [0]

    def test_oversized_page_among_normal_pages(self):
        """超大页夹在正常页之间，超大页独占一段"""
        splitter = PDFSplitter(max_size_mb=10)
        # target_max = 10MB
        # [3.0, 15.0, 3.0]: page1=15MB > 10MB
        # page0: current=3
        # page1(15MB > 10MB): current_size=3>0, split at 1 -> [0,1]; i+1<3, split at 2 -> [0,1,2]; current=0
        # page2: current=0+3=3
        page_sizes = [3.0, 15.0, 3.0]
        result = splitter._calculate_split_points(page_sizes)
        assert 0 in result
        assert 1 in result
        assert 2 in result

    def test_pages_exactly_at_target(self):
        """页面大小恰好等于目标大小"""
        splitter = PDFSplitter(max_size_mb=100)
        # target_size = 100 * 0.92 = 92MB
        # 一页92MB，刚好不触发分割
        result = splitter._calculate_split_points([92.0])
        assert result == [0]

    def test_many_small_pages_fill_segment(self):
        """大量小页面填满一段后开始新段"""
        splitter = PDFSplitter(max_size_mb=10)
        # target_size = 9.2MB
        # 20 pages * 1MB = 20MB total
        # 前9页累积9MB <= 9.2; 第10页: 9+1=10 > 9.2
        #   option1_diff = |9-9.2| = 0.2
        #   option2_diff = |10-9.2| = 0.8
        #   0.8 < 0.2 is False -> split at 10
        page_sizes = [1.0] * 20
        result = splitter._calculate_split_points(page_sizes)
        assert result[0] == 0
        # 应该有分割点
        assert len(result) >= 2


class TestEstimateSegments:
    """estimate_segments 测试 (mock PDFAnalyzer)"""

    def test_estimate_single_segment(self):
        """预估单段文件"""
        splitter = PDFSplitter(max_size_mb=200)
        page_sizes = [30.0, 30.0, 30.0]
        with patch.object(splitter.analyzer, 'get_page_sizes', return_value=page_sizes):
            count, sizes = splitter.estimate_segments('dummy.pdf')
        assert count == 1
        assert len(sizes) == 1
        assert sizes[0] == pytest.approx(90.0)

    def test_estimate_multiple_segments(self):
        """预估多段文件"""
        splitter = PDFSplitter(max_size_mb=10)
        page_sizes = [4.0, 4.0, 4.0]
        with patch.object(splitter.analyzer, 'get_page_sizes', return_value=page_sizes):
            count, sizes = splitter.estimate_segments('dummy.pdf')
        assert count == 2
        assert len(sizes) == 2
        # 第一段: 页0-1 = 8MB, 第二段: 页2 = 4MB
        assert sizes[0] == pytest.approx(8.0)
        assert sizes[1] == pytest.approx(4.0)

    def test_estimate_empty_pdf(self):
        """空PDF预估"""
        splitter = PDFSplitter()
        with patch.object(splitter.analyzer, 'get_page_sizes', return_value=[]):
            count, sizes = splitter.estimate_segments('dummy.pdf')
        assert count == 1
        assert sizes == [0]

    def test_estimate_segment_sizes_sum_to_total(self):
        """所有分段大小之和应等于总页面大小"""
        splitter = PDFSplitter(max_size_mb=10)
        page_sizes = [3.0, 4.0, 3.0, 5.0, 2.0]
        with patch.object(splitter.analyzer, 'get_page_sizes', return_value=page_sizes):
            count, sizes = splitter.estimate_segments('dummy.pdf')
        assert sum(sizes) == pytest.approx(sum(page_sizes))
