#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF压缩工具 - 主入口

功能：
- 自动检测PDF文件大小
- 超过200MB时执行压缩
- 保持清晰度和可读性
- 支持分段处理超大文件

使用方法：
    python main.py              # 启动图形界面
    python main.py --cli input.pdf  # 命令行模式

作者: PDF Tool
版本: 1.0.0
"""

import sys
import argparse
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def run_gui():
    """启动图形界面"""
    try:
        from src.gui.main_window import run_app
        run_app()
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        sys.exit(1)


def run_cli(input_path: str, output_path: str = None, target_size: float = 200):
    """命令行模式运行"""
    from src.core.compressor import compress_pdf
    from src.utils.file_utils import validate_pdf, get_file_size_mb, format_size

    # 验证文件
    if not validate_pdf(input_path):
        print(f"错误: {input_path} 不是有效的PDF文件")
        return 1

    original_size = get_file_size_mb(input_path)
    print(f"原始文件大小: {format_size(original_size)}")

    # 检查是否需要压缩
    if original_size <= target_size:
        print(f"文件已小于目标大小 {target_size}MB，无需压缩")
        return 0

    # 执行压缩
    def progress_callback(progress: int, message: str):
        print(f"[{progress}%] {message}")

    print(f"开始压缩，目标大小: {target_size}MB...")
    result = compress_pdf(
        input_path,
        output_path,
        target_size_mb=target_size,
        progress_callback=progress_callback
    )

    # 输出结果
    if result.success:
        print(f"\n压缩完成!")
        print(f"最终大小: {format_size(result.final_size_mb)}")
        print(f"压缩率: {(1 - result.compression_ratio) * 100:.1f}%")

        if result.was_split:
            print(f"已分为 {len(result.output_files)} 个文件:")
            for f in result.output_files:
                print(f"  - {f}")
        else:
            print(f"输出文件: {result.output_files[0]}")

        return 0
    else:
        print(f"\n压缩失败: {result.message}")
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="PDF压缩工具 - 将PDF文件压缩到指定大小",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python main.py                          # 启动图形界面
    python main.py --cli document.pdf       # 压缩文件（命令行）
    python main.py --cli input.pdf -o output.pdf  # 指定输出文件
    python main.py --cli input.pdf -t 100   # 目标大小100MB
        """
    )

    parser.add_argument(
        '--cli',
        metavar='INPUT',
        help='命令行模式，指定输入PDF文件'
    )

    parser.add_argument(
        '-o', '--output',
        metavar='OUTPUT',
        help='输出文件路径（命令行模式）'
    )

    parser.add_argument(
        '-t', '--target',
        type=float,
        default=200,
        metavar='SIZE',
        help='目标大小（MB），默认200MB'
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version='PDF压缩工具 v1.0.0'
    )

    args = parser.parse_args()

    if args.cli:
        # 命令行模式
        return run_cli(args.cli, args.output, args.target)
    else:
        # 图形界面模式
        run_gui()
        return 0


if __name__ == "__main__":
    sys.exit(main())