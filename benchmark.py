# -*- coding: utf-8 -*-
"""PDF 压缩性能对比脚本

用法:
    python benchmark.py input.pdf
    python benchmark.py input.pdf --target 200 --quality 85
"""
import sys
import time
import argparse
from pathlib import Path

project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.compressor import compress_pdf
from src.utils.file_utils import validate_pdf, get_file_size_mb


def format_size(size_mb: float) -> str:
    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} GB"
    if size_mb >= 1:
        return f"{size_mb:.2f} MB"
    return f"{size_mb * 1024:.2f} KB"


def print_table(rows):
    headers = ["模式", "后端", "耗时(秒)", "原始大小", "输出大小", "压缩率", "状态", "输出文件"]
    table = [headers] + rows
    widths = [max(len(str(row[i])) for row in table) for i in range(len(headers))]

    def fmt(row):
        return " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))

    print("\n" + fmt(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))


def run_case(input_path: str, target_size: float, quality: int, mode: str, backend: str):
    output_path = str(Path(input_path).with_name(f"{Path(input_path).stem}_{mode}_{backend}.pdf"))
    start = time.perf_counter()
    result = compress_pdf(
        input_path=input_path,
        output_path=output_path,
        target_size_mb=target_size,
        quality=quality,
        force_compress=True,
        use_multithreading=True,
        compression_mode=mode,
        backend=backend,
    )
    elapsed = time.perf_counter() - start

    if result.success:
        final_size = result.final_size_mb
        ratio = f"{(1 - result.compression_ratio) * 100:.1f}%"
        status = "成功"
        output_name = Path(result.output_files[0]).name if result.output_files else "-"
    else:
        final_size = 0
        ratio = "-"
        status = f"失败: {result.message}"
        output_name = "-"

    return [
        mode,
        backend,
        f"{elapsed:.2f}",
        format_size(result.original_size_mb),
        format_size(final_size) if final_size else "-",
        ratio,
        status,
        output_name,
    ]


def main():
    parser = argparse.ArgumentParser(description="PDF 压缩性能对比脚本")
    parser.add_argument("input", help="输入 PDF 文件路径")
    parser.add_argument("--target", type=float, default=200, help="目标大小 MB，默认 200")
    parser.add_argument("--quality", type=int, default=85, help="质量，默认 85")
    args = parser.parse_args()

    input_path = str(Path(args.input).resolve())
    if not Path(input_path).exists():
        print(f"文件不存在: {input_path}")
        return 1
    if not validate_pdf(input_path):
        print(f"不是有效 PDF: {input_path}")
        return 1

    original_size = get_file_size_mb(input_path)
    print("=" * 80)
    print("PDF 压缩性能对比")
    print("=" * 80)
    print(f"输入文件: {input_path}")
    print(f"原始大小: {format_size(original_size)}")
    print(f"目标大小: {args.target:.1f} MB")
    print(f"质量参数: {args.quality}")

    cases = [
        ("fast", "auto"),
        ("fast", "ghostscript"),
        ("balanced", "auto"),
        ("balanced", "python"),
    ]

    rows = []
    for mode, backend in cases:
        print(f"\n>>> 测试中: mode={mode}, backend={backend}")
        try:
            rows.append(run_case(input_path, args.target, args.quality, mode, backend))
        except Exception as e:
            rows.append([mode, backend, "-", format_size(original_size), "-", "-", f"异常: {e}", "-"])

    print_table(rows)
    print("\n说明:")
    print("- fast 更偏向速度")
    print("- balanced 更偏向体积/质量平衡")
    print("- auto 会自动选择可用后端")
    print("- ghostscript 若不可用会自动回退")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
