"""图像处理模块"""
import io
from typing import Tuple, Optional
from PIL import Image

from ..utils.config import get_config


class ImageProcessor:
    """图像处理器"""

    def __init__(self):
        self.config = get_config()

    def compress_image(
        self,
        image_data: bytes,
        quality: Optional[int] = None,
        max_dpi: Optional[int] = None,
        max_dimension: Optional[int] = None
    ) -> Tuple[bytes, bool]:
        """
        压缩图像

        Args:
            image_data: 原始图像数据
            quality: JPEG质量 (1-100)
            max_dpi: 最大DPI
            max_dimension: 最大尺寸（宽或高）

        Returns:
            (压缩后的数据, 是否成功)
        """
        if quality is None:
            quality = self.config.default_quality
        if max_dpi is None:
            max_dpi = self.config.max_dpi

        try:
            # 打开图像
            img = Image.open(io.BytesIO(image_data))
            original_size = len(image_data)

            # 记录原始模式
            original_mode = img.mode

            # 调整尺寸（如果需要）
            if max_dimension:
                img = self._resize_if_needed(img, max_dimension)

            # 根据图像模式选择压缩策略
            if img.mode in ('RGBA', 'LA', 'P'):
                # 有透明通道的图像，保持为PNG或转换为RGB
                compressed_data = self._compress_transparent(img, quality)
            elif img.mode == '1':
                # 黑白图像
                compressed_data = self._compress_grayscale(img, quality)
            else:
                # RGB或其他模式，转为JPEG压缩
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                compressed_data = self._compress_rgb(img, quality)

            # 只有压缩后更小才使用
            if len(compressed_data) < original_size:
                return compressed_data, True
            else:
                return image_data, False

        except Exception:
            return image_data, False

    def _resize_if_needed(
        self,
        img: Image.Image,
        max_dimension: int
    ) -> Image.Image:
        """如果图像超过最大尺寸则缩小"""
        width, height = img.size

        if max(width, height) <= max_dimension:
            return img

        # 计算缩放比例
        ratio = max_dimension / max(width, height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)

        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _compress_rgb(self, img: Image.Image, quality: int) -> bytes:
        """压缩RGB图像为JPEG"""
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        return buffer.getvalue()

    def _compress_transparent(self, img: Image.Image, quality: int) -> bytes:
        """压缩带透明通道的图像"""
        buffer = io.BytesIO()

        # 尝试保持PNG格式（无损压缩）
        img.save(buffer, format='PNG', optimize=True)
        png_size = buffer.tell()

        # 也尝试转换为JPEG（有损但更小）
        if img.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            rgb_img = background
        elif img.mode == 'LA':
            background = Image.new('L', img.size, 255)
            background.paste(img, mask=img.split()[1])
            rgb_img = background.convert('RGB')
        elif img.mode == 'P':
            rgb_img = img.convert('RGB')
        else:
            rgb_img = img.convert('RGB')

        jpeg_buffer = io.BytesIO()
        rgb_img.save(jpeg_buffer, format='JPEG', quality=quality, optimize=True)
        jpeg_size = jpeg_buffer.tell()

        # 选择更小的一个
        if jpeg_size < png_size:
            return jpeg_buffer.getvalue()
        else:
            buffer.seek(0)
            return buffer.getvalue()

    def _compress_grayscale(self, img: Image.Image, quality: int) -> bytes:
        """压缩灰度图像"""
        buffer = io.BytesIO()

        # 转换为RGB以使用JPEG压缩
        rgb_img = img.convert('RGB')
        rgb_img.save(buffer, format='JPEG', quality=quality, optimize=True)

        return buffer.getvalue()

    def reduce_dpi(
        self,
        image_data: bytes,
        current_dpi: int,
        target_dpi: int
    ) -> Tuple[bytes, bool]:
        """降低图像DPI"""
        if current_dpi <= target_dpi:
            return image_data, False

        try:
            img = Image.open(io.BytesIO(image_data))

            # 计算缩放比例
            ratio = target_dpi / current_dpi
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)

            # 调整大小
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 保存
            buffer = io.BytesIO()
            if resized.mode == 'RGB':
                resized.save(buffer, format='JPEG', quality=85, optimize=True)
            else:
                resized.save(buffer, format='PNG', optimize=True)

            return buffer.getvalue(), True

        except Exception:
            return image_data, False

    def get_image_info(self, image_data: bytes) -> dict:
        """获取图像信息"""
        try:
            img = Image.open(io.BytesIO(image_data))
            return {
                'width': img.width,
                'height': img.height,
                'mode': img.mode,
                'format': img.format,
                'size_bytes': len(image_data)
            }
        except Exception:
            return {}


def compress_image_data(
    image_data: bytes,
    quality: int = 85,
    max_dimension: Optional[int] = None
) -> Tuple[bytes, bool]:
    """便捷函数：压缩图像数据"""
    processor = ImageProcessor()
    return processor.compress_image(image_data, quality, max_dimension=max_dimension)