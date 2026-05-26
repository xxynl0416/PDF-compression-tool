# -*- coding: utf-8 -*-
"""PDF分段处理模块 - 精确控制每段大小"""
import os
from typing import List, Optional, Tuple
import fitz  # PyMuPDF

from .analyzer import PDFAnalyzer
from ..utils.file_utils import (
    get_file_size_mb,
    generate_segment_path,
    format_size
)
from ..utils.logger import setup_logger


class PDFSplitter:
    """PDF分段器 - 精确控制每段大小"""

    def __init__(self, max_size_mb: float = 200, size_tolerance: float = 0.05,
                 segment_suffix: str = "_part"):
        self.max_size_mb = max_size_mb
        self.size_tolerance = size_tolerance
        self.segment_suffix = segment_suffix
        self.target_min = self.max_size_mb * (1 - size_tolerance)
        self.target_max = self.max_size_mb
        self.analyzer = PDFAnalyzer()
        self.logger = setup_logger("pdf_splitter")

    def split(
        self,
        input_path: str,
        output_base_path: Optional[str] = None
    ) -> List[str]:
        """
        按大小分段PDF文件 - 确保每段不超过目标大小

        Args:
            input_path: 输入PDF文件路径
            output_base_path: 输出文件基础路径（可选）

        Returns:
            分段文件路径列表
        """
        self.logger.info(f"开始分段处理: {input_path}")
        self.logger.info(f"目标大小: {self.target_min:.1f} - {self.target_max:.1f} MB")

        # 获取每页大小估算
        page_sizes = self.analyzer.get_page_sizes(input_path)
        total_pages = len(page_sizes)

        if total_pages == 0:
            self.logger.warning("PDF没有页面，无法分段")
            return []

        # 计算分割点（基于估算）
        split_points = self._calculate_split_points(page_sizes)

        self.logger.info(
            f"计划分为 {len(split_points)} 段，"
            f"分割点: {[p + 1 for p in split_points[:-1]]}页后"
        )

        # 生成分段文件并验证大小
        output_files = self._create_segments_with_validation(
            input_path, split_points, page_sizes, output_base_path
        )

        self.logger.info(f"分段完成，生成 {len(output_files)} 个文件")
        return output_files

    def _calculate_split_points(self, page_sizes: List[float]) -> List[int]:
        """
        计算分割点 - 目标是让每段尽可能接近目标大小

        Args:
            page_sizes: 每页大小列表（MB）

        Returns:
            分割点列表（每段的起始页码）
        """
        split_points = [0]
        current_size = 0
        target_size = self.target_max * 0.92  # 目标是最大值的92%，留出安全边际

        for i, size in enumerate(page_sizes):
            # 检查单页是否超过限制
            if size > self.target_max:
                self.logger.warning(
                    f"第 {i + 1} 页大小 ({format_size(size)}) "
                    f"超过限制 ({format_size(self.target_max)})，将单独分段"
                )
                if current_size > 0:
                    split_points.append(i)
                if i + 1 < len(page_sizes):
                    split_points.append(i + 1)
                current_size = 0
                continue

            # 智能判断：是否应该在当前页之前分段
            # 目标：让每段尽可能接近目标大小
            if current_size + size > target_size:
                # 检查是现在分段还是下一页分段更接近目标
                if current_size > 0:
                    # 当前段已有内容，检查两种选择
                    option1_diff = abs(current_size - target_size)  # 现在分段
                    option2_diff = abs(current_size + size - target_size)  # 加上这页再分段
                    
                    # 如果加上这页更接近目标且不超过最大值
                    if option2_diff < option1_diff and current_size + size <= self.target_max:
                        current_size += size
                    else:
                        split_points.append(i)
                        current_size = size
                else:
                    current_size = size
            else:
                current_size += size

        return split_points

    def _create_segments_with_validation(
        self,
        input_path: str,
        initial_split_points: List[int],
        page_sizes: List[float],
        output_base_path: Optional[str] = None
    ) -> List[str]:
        """
        创建分段文件并验证大小 - 如果超过目标则重新分段

        Args:
            input_path: 输入文件路径
            initial_split_points: 初始分割点列表
            page_sizes: 每页大小估算
            output_base_path: 输出基础路径

        Returns:
            分段文件路径列表
        """
        doc = fitz.open(input_path)
        total_pages = len(doc)
        output_files = []
        
        try:
            split_points = initial_split_points.copy()
            
            for i, start_page in enumerate(split_points):
                # 确定结束页
                if i + 1 < len(split_points):
                    end_page = split_points[i + 1]
                else:
                    end_page = total_pages

                # 生成输出路径
                output_path = self._get_output_path(input_path, output_base_path, i + 1)

                # 创建新文档
                new_doc = fitz.open()

                try:
                    new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
                    new_doc.save(output_path, garbage=4, deflate=True, clean=True)
                    
                    segment_size = get_file_size_mb(output_path)
                    
                    # 验证大小，如果超过目标则需要重新分段
                    if segment_size > self.target_max and (end_page - start_page) > 1:
                        self.logger.warning(
                            f"分段 {i + 1} 大小 {format_size(segment_size)} 超过目标，重新分段"
                        )
                        
                        # 删除当前分段
                        new_doc.close()
                        os.remove(output_path)
                        
                        # 递归分段当前段
                        sub_pages = list(range(start_page, end_page))
                        sub_sizes = page_sizes[start_page:end_page]
                        sub_split_points = self._calculate_split_points(sub_sizes)
                        
                        # 创建子分段
                        for j, sub_start in enumerate(sub_split_points):
                            sub_end = sub_split_points[j + 1] if j + 1 < len(sub_split_points) else len(sub_pages)
                            
                            sub_output_path = self._get_output_path(
                                input_path, output_base_path, len(output_files) + 1
                            )
                            
                            sub_doc = fitz.open()
                            try:
                                sub_doc.insert_pdf(
                                    doc,
                                    from_page=start_page + sub_start,
                                    to_page=start_page + sub_end - 1
                                )
                                sub_doc.save(sub_output_path, garbage=4, deflate=True, clean=True)
                            finally:
                                sub_doc.close()
                            
                            sub_size = get_file_size_mb(sub_output_path)
                            output_files.append(sub_output_path)
                            self.logger.info(
                                f"子分段 {len(output_files)}: 页码 {start_page + sub_start + 1}-{start_page + sub_end}, "
                                f"大小 {format_size(sub_size)}"
                            )
                    else:
                        output_files.append(output_path)
                        self.logger.info(
                            f"分段 {i + 1}: 页码 {start_page + 1}-{end_page}, "
                            f"大小 {format_size(segment_size)}"
                        )

                finally:
                    new_doc.close()

        finally:
            doc.close()

        return output_files

    def _get_output_path(self, input_path: str, output_base_path: Optional[str], segment_num: int) -> str:
        """生成输出路径"""
        if output_base_path:
            return generate_segment_path(output_base_path, segment_num, self.segment_suffix)
        else:
            return generate_segment_path(input_path, segment_num, self.segment_suffix)

    def split_by_pages(
        self,
        input_path: str,
        pages_per_segment: int,
        output_base_path: Optional[str] = None
    ) -> List[str]:
        """
        按页数分段PDF文件

        Args:
            input_path: 输入PDF文件路径
            pages_per_segment: 每段页数
            output_base_path: 输出文件基础路径

        Returns:
            分段文件路径列表
        """
        doc = fitz.open(input_path)
        total_pages = len(doc)
        output_files = []

        try:
            for start in range(0, total_pages, pages_per_segment):
                end = min(start + pages_per_segment, total_pages)

                segment_num = start // pages_per_segment + 1
                output_path = self._get_output_path(input_path, output_base_path, segment_num)

                new_doc = fitz.open()
                try:
                    new_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
                    new_doc.save(output_path, garbage=4, deflate=True, clean=True)
                    output_files.append(output_path)
                finally:
                    new_doc.close()

        finally:
            doc.close()

        return output_files

    def estimate_segments(self, input_path: str) -> Tuple[int, List[float]]:
        """
        预估分段数量和每段大小

        Args:
            input_path: 输入PDF文件路径

        Returns:
            (分段数量, 每段大小列表)
        """
        page_sizes = self.analyzer.get_page_sizes(input_path)
        split_points = self._calculate_split_points(page_sizes)

        segment_sizes = []
        for i, start in enumerate(split_points):
            if i + 1 < len(split_points):
                end = split_points[i + 1]
            else:
                end = len(page_sizes)

            segment_size = sum(page_sizes[start:end])
            segment_sizes.append(segment_size)

        return len(split_points), segment_sizes


def split_pdf(
    input_path: str,
    max_size_mb: float = 200,
    output_base_path: Optional[str] = None,
    size_tolerance: float = 0.05
) -> List[str]:
    """
    便捷函数：分段PDF文件

    Args:
        input_path: 输入文件路径
        max_size_mb: 每段最大大小（MB）
        output_base_path: 输出基础路径
        size_tolerance: 大小容差

    Returns:
        分段文件路径列表
    """
    splitter = PDFSplitter(max_size_mb, size_tolerance)
    return splitter.split(input_path, output_base_path)