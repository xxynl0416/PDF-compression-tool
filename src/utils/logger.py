"""日志模块"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "pdf_tool",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> logging.Logger:
    """设置并返回日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 仅在没有处理器时添加，避免重复清除
    if logger.handlers:
        return logger

    # 创建格式化器
    formatter = logging.Formatter(format_str)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定了日志文件）
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"无法创建日志文件: {e}")

    return logger


class CompressionLogger:
    """压缩过程专用日志类"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.stages = []
        self.current_stage = None

    def start_compression(self, input_file: str, original_size: float):
        """记录压缩开始"""
        self.logger.info(f"开始压缩: {input_file}")
        self.logger.info(f"原始大小: {original_size:.2f} MB")

    def start_stage(self, stage_name: str):
        """记录阶段开始"""
        self.current_stage = stage_name
        self.logger.info(f"开始阶段: {stage_name}")

    def end_stage(self, stage_name: str, result_size: float):
        """记录阶段结束"""
        self.logger.info(f"阶段完成: {stage_name}, 当前大小: {result_size:.2f} MB")
        self.stages.append({
            'stage': stage_name,
            'result_size': result_size
        })

    def log_image_processing(self, current: int, total: int, image_info: str = ""):
        """记录图像处理进度"""
        msg = f"处理图像: {current}/{total}"
        if image_info:
            msg += f" - {image_info}"
        self.logger.debug(msg)

    def log_split(self, segment_num: int, pages: list, size: float):
        """记录分段处理"""
        self.logger.info(
            f"分段 {segment_num}: 页码 {pages[0]+1}-{pages[-1]+1}, "
            f"大小: {size:.2f} MB"
        )

    def end_compression(self, success: bool, output_files: list, final_size: float):
        """记录压缩结束"""
        if success:
            if len(output_files) == 1:
                self.logger.info(f"压缩完成: {output_files[0]}")
            else:
                self.logger.info(f"压缩完成, 生成 {len(output_files)} 个分段文件:")
                for f in output_files:
                    self.logger.info(f"  - {f}")
            self.logger.info(f"最终大小: {final_size:.2f} MB")
        else:
            self.logger.error("压缩失败")

    def log_error(self, error: Exception, context: str = ""):
        """记录错误"""
        msg = f"错误: {type(error).__name__}: {error}"
        if context:
            msg = f"{context} - {msg}"
        self.logger.error(msg)