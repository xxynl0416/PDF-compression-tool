"""Tests for src.utils.file_utils"""
import sys
from pathlib import Path
from unittest.mock import patch
import tempfile
import os
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.file_utils import (
    get_unique_output_path,
    validate_pdf,
    format_size,
    get_file_size_mb,
    check_disk_space,
)


class TestGetUniqueOutputPath:
    def test_file_does_not_exist_returns_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "report.pdf")
            result = get_unique_output_path(input_path, "_compressed")
            expected = os.path.join(tmpdir, "report_compressed.pdf")
            assert result == expected

    def test_file_exists_returns_path_with_1_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "report.pdf")
            # Create the default output file so it already exists
            default_output = os.path.join(tmpdir, "report_compressed.pdf")
            with open(default_output, "w") as f:
                f.write("placeholder")

            result = get_unique_output_path(input_path, "_compressed")
            expected = os.path.join(tmpdir, "report_compressed_1.pdf")
            assert result == expected

    def test_raises_oserror_when_counter_exceeds_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "report.pdf")
            with patch("src.utils.file_utils.os.path.exists", return_value=True):
                import pytest
                with pytest.raises(OSError):
                    get_unique_output_path(input_path, "_compressed")


class TestValidatePdf:
    def test_nonexistent_file_returns_false(self):
        result = validate_pdf("/nonexistent/path/fake.pdf")
        assert result is False

    def test_valid_pdf_header_returns_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "valid.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4\n%Some PDF content here")
            assert validate_pdf(pdf_path) is True

    def test_garbage_bytes_returns_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "garbage.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"\x00\x01\x02\x03\x04random bytes")
            assert validate_pdf(pdf_path) is False


class TestFormatSize:
    def test_half_mb_returns_kb(self):
        assert format_size(0.5) == "512.00 KB"

    def test_one_and_half_mb(self):
        assert format_size(1.5) == "1.50 MB"

    def test_1500_mb_returns_gb(self):
        assert format_size(1500) == "1.46 GB"


class TestGetFileSizeMb:
    def test_returns_correct_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.bin")
            size_bytes = 2 * 1024 * 1024  # 2 MB
            with open(file_path, "wb") as f:
                f.write(b"\x00" * size_bytes)

            result = get_file_size_mb(file_path)
            assert abs(result - 2.0) < 1e-6


class TestCheckDiskSpace:
    @patch("src.utils.file_utils.shutil.disk_usage")
    def test_enough_space_returns_true(self, mock_disk_usage):
        # free = 500 MB in bytes
        mock_disk_usage.return_value = (1000 * 1024 * 1024, 0, 500 * 1024 * 1024)
        assert check_disk_space("/some/path", 100) is True

    @patch("src.utils.file_utils.shutil.disk_usage")
    def test_not_enough_space_returns_false(self, mock_disk_usage):
        # free = 50 MB in bytes
        mock_disk_usage.return_value = (1000 * 1024 * 1024, 0, 50 * 1024 * 1024)
        assert check_disk_space("/some/path", 100) is False
