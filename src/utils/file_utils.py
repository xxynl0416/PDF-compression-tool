"""文件操作工具模块"""
import os
from pathlib import Path
from typing import Optional

# PDF文件魔数（PDF文件以 %PDF- 开头）
PDF_MAGIC = b'%PDF-'


def get_file_size_mb(file_path: str) -> float:
    """获取文件大小（MB）"""
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)


def get_file_size_bytes(file_path: str) -> int:
    """获取文件大小（字节）"""
    return os.path.getsize(file_path)


def validate_pdf(file_path: str) -> bool:
    """验证文件是否为有效的PDF

    PDF文件通常以 %PDF- 开头（如 %PDF-1.4, %PDF-1.7 等）
    部分PDF可能包含BOM或前导空白字符
    """
    if not os.path.exists(file_path):
        return False

    try:
        with open(file_path, 'rb') as f:
            # 读取前1024字节以处理可能有BOM或前导空格的情况
            header = f.read(1024)

            # 检查是否以 %PDF 开头（标准情况）
            if header.startswith(b'%PDF'):
                return True

            # 检查是否有BOM (UTF-8 BOM: EF BB BF)
            if header.startswith(b'\xef\xbb\xbf'):
                # 跳过BOM后检查
                if header[3:].startswith(b'%PDF'):
                    return True

            # 某些PDF可能有前导空白或换行
            stripped = header.lstrip()
            if stripped.startswith(b'%PDF'):
                return True

            return False
    except (IOError, OSError, PermissionError):
        return False


def generate_output_path(input_path: str, suffix: str = "_compressed") -> str:
    """生成输出文件路径"""
    path = Path(input_path)
    parent = path.parent
    stem = path.stem
    extension = path.suffix

    output_name = f"{stem}{suffix}{extension}"
    return str(parent / output_name)


def generate_segment_path(input_path: str, segment_num: int, suffix: str = "_part") -> str:
    """生成分段文件路径"""
    path = Path(input_path)
    parent = path.parent
    stem = path.stem
    extension = path.suffix

    output_name = f"{stem}{suffix}{segment_num}{extension}"
    return str(parent / output_name)


def ensure_directory(dir_path: str) -> bool:
    """确保目录存在，不存在则创建"""
    try:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        return True
    except (IOError, OSError):
        return False


def check_disk_space(file_path: str, required_mb: float) -> bool:
    """检查磁盘空间是否足够"""
    try:
        path = Path(file_path)
        if path.is_file():
            directory = path.parent
        else:
            directory = path

        # 获取磁盘使用情况
        total, used, free = os.statvfs(directory).f_blocks, 0, 0
        # Windows 系统使用不同方式
        import shutil
        total, used, free = shutil.disk_usage(directory)

        free_mb = free / (1024 * 1024)
        return free_mb >= required_mb
    except Exception:
        # 无法检查时假设空间足够
        return True


def get_unique_output_path(input_path: str, suffix: str = "_compressed") -> str:
    """生成唯一的输出文件路径（避免覆盖已存在的文件）"""
    output_path = generate_output_path(input_path, suffix)

    if not os.path.exists(output_path):
        return output_path

    # 如果文件已存在，添加数字后缀
    counter = 1
    path = Path(input_path)
    parent = path.parent
    stem = path.stem
    extension = path.suffix

    while True:
        output_name = f"{stem}{suffix}_{counter}{extension}"
        output_path = str(parent / output_name)
        if not os.path.exists(output_path):
            return output_path
        counter += 1


def format_size(size_mb: float) -> str:
    """格式化文件大小显示"""
    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} GB"
    elif size_mb >= 1:
        return f"{size_mb:.2f} MB"
    else:
        return f"{size_mb * 1024:.2f} KB"


def open_file_with_default_app(file_path: str) -> bool:
    """使用系统默认应用程序打开文件

    Args:
        file_path: 文件路径

    Returns:
        是否成功打开
    """
    import sys
    import subprocess

    if not os.path.exists(file_path):
        return False

    try:
        file_path = os.path.abspath(file_path)

        if sys.platform == 'win32':
            # Windows: 使用 startfile
            os.startfile(file_path)
        elif sys.platform == 'darwin':
            # macOS: 使用 open 命令
            subprocess.run(['open', file_path], check=True)
        else:
            # Linux: 使用 xdg-open
            subprocess.run(['xdg-open', file_path], check=True)

        return True
    except Exception:
        return False


def open_directory(directory_path: str) -> bool:
    """打开目录（在文件管理器中显示）

    Args:
        directory_path: 目录路径

    Returns:
        是否成功打开
    """
    import sys
    import subprocess

    path = Path(directory_path)
    if not path.exists():
        return False

    try:
        directory_path = os.path.abspath(directory_path)

        if sys.platform == 'win32':
            # Windows: 使用 explorer 打开目录
            os.startfile(directory_path)
        elif sys.platform == 'darwin':
            # macOS: 使用 open 命令
            subprocess.run(['open', directory_path], check=True)
        else:
            # Linux: 使用 xdg-open
            subprocess.run(['xdg-open', directory_path], check=True)

        return True
    except Exception:
        return False


def open_file_in_explorer(file_path: str) -> bool:
    """在文件管理器中定位并选中文件

    Args:
        file_path: 文件路径

    Returns:
        是否成功打开
    """
    import sys
    import subprocess

    if not os.path.exists(file_path):
        return False

    try:
        file_path = os.path.abspath(file_path)

        if sys.platform == 'win32':
            # Windows: 使用 explorer /select 定位文件
            subprocess.run(['explorer', '/select,', file_path], check=False)
        elif sys.platform == 'darwin':
            # macOS: 使用 open -R 定位文件
            subprocess.run(['open', '-R', file_path], check=True)
        else:
            # Linux: 打开所在目录
            parent_dir = str(Path(file_path).parent)
            subprocess.run(['xdg-open', parent_dir], check=True)

        return True
    except Exception:
        return False