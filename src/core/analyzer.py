"""PDF分析器模块"""
from dataclasses import dataclass
from typing import List, Optional
import fitz  # PyMuPDF

from ..utils.file_utils import get_file_size_mb, get_file_size_bytes


@dataclass
class ImageInfo:
    """图像信息数据类"""
    index: int
    page_num: int
    width: int
    height: int
    colorspace: str
    xref: int  # PDF内部引用
    size_bytes: int

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def resolution(self) -> int:
        """估算分辨率"""
        return max(self.width, self.height)


@dataclass
class PageInfo:
    """页面信息数据类"""
    page_num: int
    width: float
    height: float
    image_count: int
    text_length: int


@dataclass
class PDFInfo:
    """PDF信息数据类"""
    file_path: str
    file_size_mb: float
    page_count: int
    image_count: int
    has_text: bool
    is_encrypted: bool
    images: List[ImageInfo]
    pages: List[PageInfo]

    @property
    def total_image_size_mb(self) -> float:
        """所有图像的总大小"""
        return sum(img.size_mb for img in self.images)

    @property
    def average_page_size_mb(self) -> float:
        """平均每页大小"""
        if self.page_count == 0:
            return 0
        return self.file_size_mb / self.page_count


class PDFAnalyzer:
    """PDF分析器"""

    def __init__(self):
        self._doc: Optional[fitz.Document] = None

    def analyze(self, file_path: str) -> PDFInfo:
        """快速分析PDF文件，避免深度提取所有图片数据导致性能过慢"""
        self._doc = fitz.open(file_path)

        try:
            file_size_mb = get_file_size_mb(file_path)
            page_count = len(self._doc)
            is_encrypted = self._doc.is_encrypted

            images: List[ImageInfo] = []
            pages: List[PageInfo] = []
            total_text_length = 0
            total_image_count = 0

            for page_num in range(page_count):
                page = self._doc[page_num]

                # 文本信息：保留，但只做一次轻量提取
                try:
                    text = page.get_text("text")
                    text_length = len(text)
                except Exception:
                    text_length = 0
                total_text_length += text_length

                # 图像信息：只统计数量，不做 extract_image 深度提取
                try:
                    image_list = page.get_images(full=False)
                    image_count = len(image_list)
                except Exception:
                    image_count = 0
                total_image_count += image_count

                page_rect = page.rect
                pages.append(PageInfo(
                    page_num=page_num,
                    width=page_rect.width,
                    height=page_rect.height,
                    image_count=image_count,
                    text_length=text_length
                ))

            return PDFInfo(
                file_path=file_path,
                file_size_mb=file_size_mb,
                page_count=page_count,
                image_count=total_image_count,
                has_text=total_text_length > 0,
                is_encrypted=is_encrypted,
                images=images,
                pages=pages
            )

        finally:
            self._doc.close()
            self._doc = None

    def _extract_page_images(
        self,
        page: fitz.Page,
        page_num: int,
        start_index: int
    ) -> List[ImageInfo]:
        """提取页面中的所有图像信息"""
        images = []

        image_list = page.get_images(full=True)
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]

            try:
                base_image = self._doc.extract_image(xref)
                if base_image:
                    images.append(ImageInfo(
                        index=start_index + img_index,
                        page_num=page_num,
                        width=base_image["width"],
                        height=base_image["height"],
                        colorspace=base_image.get("colorspace", "unknown"),
                        xref=xref,
                        size_bytes=len(base_image["image"])
                    ))
            except Exception:
                pass

        return images

    def get_page_sizes(self, file_path: str) -> List[float]:
        """获取每页的估算大小（MB）"""
        doc = fitz.open(file_path)
        try:
            total_size = get_file_size_bytes(file_path)
            page_count = len(doc)

            if page_count == 0:
                return []

            page_weights = []
            for page_num in range(page_count):
                page = doc[page_num]
                images = page.get_images(full=False)
                weight = 1 + len(images)
                page_weights.append(weight)

            total_weight = sum(page_weights)
            if total_weight == 0:
                avg_size = total_size / page_count / (1024 * 1024)
                return [avg_size] * page_count

            return [
                (total_size * w / total_weight) / (1024 * 1024)
                for w in page_weights
            ]

        finally:
            doc.close()

    def quick_check(self, file_path: str) -> dict:
        """快速检查PDF基本信息"""
        doc = fitz.open(file_path)
        try:
            return {
                'page_count': len(doc),
                'is_encrypted': doc.is_encrypted,
                'file_size_mb': get_file_size_mb(file_path),
                'metadata': doc.metadata
            }
        finally:
            doc.close()

    def estimate_compression_potential(self, file_path: str) -> float:
        """预估压缩潜力（返回预估压缩率）"""
        info = self.analyze(file_path)

        if info.page_count == 0:
            return 0

        image_ratio = info.image_count / info.page_count if info.page_count > 0 else 0

        if image_ratio > 1.5:
            return 0.6
        elif image_ratio > 0.5:
            return 0.75
        else:
            return 0.9


def analyze_pdf(file_path: str) -> PDFInfo:
    """便捷函数：分析PDF文件"""
    analyzer = PDFAnalyzer()
    return analyzer.analyze(file_path)
