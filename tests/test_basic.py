# -*- coding: utf-8 -*-
"""测试脚本 - 验证PDF压缩工具核心功能"""
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    print("1. 测试模块导入...")
    try:
        from src.utils import file_utils, logger, config
        from src.core import analyzer, compressor, splitter
        from src.database import task_db
        print("   [OK] 模块导入成功")
        return True
    except ImportError as e:
        print(f"   [FAIL] 模块导入失败: {e}")
        return False


def test_config():
    print("\n2. 测试配置加载...")
    from src.utils.config import load_config
    cfg = load_config()
    print(f"   目标大小: {cfg.target_size_mb} MB")
    print(f"   默认质量: {cfg.default_quality}")
    assert cfg.compression_mode in ('fast', 'balanced', 'high_quality')
    assert cfg.compression_backend in ('auto', 'python', 'ghostscript')
    print("   [OK] 配置加载成功")
    return True


def test_file_utils():
    print("\n3. 测试文件工具...")
    from src.utils.file_utils import format_size, generate_output_path, generate_segment_path
    assert format_size(0.5) == "512.00 KB"
    assert format_size(100) == "100.00 MB"
    assert format_size(1500) == "1.46 GB"
    output = generate_output_path("C:/test/doc.pdf")
    expected = str(Path("C:/test") / "doc_compressed.pdf")
    assert output == expected
    segment = generate_segment_path("C:/test/doc.pdf", 1)
    expected_segment = str(Path("C:/test") / "doc_part1.pdf")
    assert segment == expected_segment
    print("   [OK] 文件工具测试通过")
    return True


def test_analyzer():
    print("\n4. 测试PDF分析器...")
    from src.core.analyzer import PDFAnalyzer
    from src.utils.file_utils import validate_pdf
    analyzer = PDFAnalyzer()
    print("   [OK] 分析器实例化成功")
    assert not validate_pdf("nonexistent.pdf")
    print("   [OK] 文件验证测试通过")
    return True


def test_compressor_init():
    print("\n6. 测试压缩器初始化...")
    from src.core.compressor import PDFCompressor, CompressionResult
    from src.core.optimizer import CompressionOptimizer
    from src.core.analyzer import PDFInfo, PageInfo
    from src.core.backends.ghostscript import GhostscriptBackend

    # 测试优化器迭代次数
    fast_opt = CompressionOptimizer(200, compression_mode="fast")
    balanced_opt = CompressionOptimizer(200, compression_mode="balanced")
    high_opt = CompressionOptimizer(200, compression_mode="high_quality")
    assert fast_opt.max_iterations == 1
    assert balanced_opt.max_iterations == 2
    assert high_opt.max_iterations == 3

    # 测试压缩结果
    result = CompressionResult(True, 300, 150, ["test_compressed.pdf"], False, "测试")
    assert result.compression_ratio == 0.5

    # 测试压缩器策略
    fast = PDFCompressor(target_size_mb=200, compression_mode="fast", backend="auto")
    pdf_info = PDFInfo('dummy.pdf', 220, 10, 1, True, False, [], [PageInfo(i, 595, 842, 0, 500) for i in range(10)])
    assert fast._should_skip_image_rerender(pdf_info, 210) is True

    # 测试后端选择
    gs_backend = GhostscriptBackend("balanced", 200)
    assert gs_backend.should_try(pdf_info, "python") is False
    assert gs_backend.should_try(pdf_info, "ghostscript") is True
    print("   [OK] 压缩器策略测试通过")
    return True


def test_task_db_schema():
    print("\n7. 测试任务数据库扩展字段...")
    from src.database.task_db import TaskDatabase
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = Path(temp_dir) / 'test_tasks.db'
        db = TaskDatabase(str(test_db_path))
        ok = db.create_task(
            't1', 'a.pdf', 'a.pdf',
            {'size_mb': 1, 'page_count': 1},
            compression_mode='balanced',
            backend='python'
        )
        assert ok
        task = db.get_task('t1')
        assert task['compression_mode'] == 'balanced'
        assert task['backend'] == 'python'
    print("   [OK] 数据库字段测试通过")
    return True


def run_tests():
    print("=" * 50)
    print("PDF压缩工具 - 单元测试")
    print("=" * 50)
    tests = [
        test_imports,
        test_config,
        test_file_utils,
        test_analyzer,
        test_compressor_init,
        test_task_db_schema,
    ]
    passed = 0
    failed = 0
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   [FAIL] 测试失败: {e}")
            failed += 1
    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
