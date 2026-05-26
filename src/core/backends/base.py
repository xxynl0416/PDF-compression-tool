"""压缩后端抽象基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class BackendResult:
    """后端压缩结果"""
    output_path: Optional[str]
    success: bool
    output_size_mb: float = 0.0
    message: str = ''


class CompressionBackend(ABC):
    """压缩后端抽象接口"""

    @abstractmethod
    def compress(
        self,
        input_path: str,
        output_path: str,
        pdf_info,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> BackendResult:
        """
        执行压缩。

        Args:
            input_path: 输入 PDF 路径
            output_path: 输出 PDF 路径
            pdf_info: PDFInfo 分析结果
            progress_callback: 进度回调 (progress_pct, message)

        Returns:
            BackendResult
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用"""
        ...
