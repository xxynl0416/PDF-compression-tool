"""后端模块测试"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.analyzer import PDFInfo, PageInfo
from src.core.backends.ghostscript import GhostscriptBackend
from src.core.backends.python_render import PythonRenderBackend


def make_pdf_info(file_size_mb=100, page_count=10, image_pages=0, text_length=500):
    pages = []
    for i in range(page_count):
        img_count = 1 if i < image_pages else 0
        pages.append(PageInfo(i, 595, 842, img_count, text_length))
    return PDFInfo('test.pdf', file_size_mb, page_count, image_pages, True, False, [], pages)


class TestGhostscriptBackend:

    def test_should_try_returns_false_for_python_backend(self):
        gs = GhostscriptBackend("fast", 200)
        info = make_pdf_info()
        assert gs.should_try(info, "python") is False

    def test_should_try_returns_true_for_ghostscript_backend(self):
        gs = GhostscriptBackend("fast", 200)
        info = make_pdf_info()
        assert gs.should_try(info, "ghostscript") is True

    def test_should_try_returns_true_for_fast_mode(self):
        gs = GhostscriptBackend("fast", 200)
        info = make_pdf_info()
        assert gs.should_try(info, "auto") is True

    def test_should_try_returns_true_for_image_heavy_pdf(self):
        gs = GhostscriptBackend("balanced", 200)
        info = make_pdf_info(page_count=10, image_pages=5)
        assert gs.should_try(info, "auto") is True

    def test_should_try_returns_false_for_text_only_pdf(self):
        gs = GhostscriptBackend("balanced", 200)
        info = make_pdf_info(page_count=10, image_pages=0)
        assert gs.should_try(info, "auto") is False

    def test_estimate_gs_profile_fast_mode(self):
        gs = GhostscriptBackend("fast", 200)
        info = make_pdf_info(file_size_mb=200)
        profile = gs._estimate_gs_profile(info)
        assert profile['pdfsettings'] == '/screen'
        assert 'dpi' in profile
        assert 'jpeg_q' in profile

    def test_estimate_gs_profile_balanced_mode(self):
        gs = GhostscriptBackend("balanced", 200)
        info = make_pdf_info()
        profile = gs._estimate_gs_profile(info)
        assert profile['pdfsettings'] == '/ebook'

    def test_estimate_gs_profile_high_quality_mode(self):
        gs = GhostscriptBackend("high_quality", 200)
        info = make_pdf_info()
        profile = gs._estimate_gs_profile(info)
        assert profile['pdfsettings'] == '/printer'

    def test_build_gs_command_structure(self):
        gs = GhostscriptBackend("fast", 200)
        profile = {'pdfsettings': '/screen', 'dpi': 96, 'jpeg_q': 40}
        cmd = gs._build_gs_command("gs", "input.pdf", "output.pdf", profile)
        assert cmd[0] == "gs"
        assert "-sDEVICE=pdfwrite" in cmd
        assert "-dPDFSETTINGS=/screen" in cmd
        assert "-dColorImageResolution=96" in cmd
        assert "-dJPEGQ=40" in cmd
        assert "input.pdf" in cmd
        assert any("output.pdf" in arg for arg in cmd)

    def test_is_available_returns_false_when_no_gs(self):
        gs = GhostscriptBackend("fast", 200)
        with patch('shutil.which', return_value=None):
            assert gs.is_available() is False


class TestPythonRenderBackend:

    def test_is_available_always_true(self):
        py = PythonRenderBackend(200)
        assert py.is_available() is True
