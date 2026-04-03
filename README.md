# PDFTool

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![Backend](https://img.shields.io/badge/Backend-PyMuPDF%20%7C%20Ghostscript-orange)
![Interface](https://img.shields.io/badge/Interface-Web%20%7C%20GUI%20%7C%20CLI-purple)

一个支持 **Web / GUI / CLI** 的 PDF 压缩工具，提供多种压缩模式与后端选择，适合日常办公、扫描件压缩与团队内部使用。

## 截图 / 说明

- Web：适合团队共享使用
- GUI：适合桌面端单机使用
- CLI：适合脚本化和批处理

## 特性

- 支持 **Web / GUI / CLI** 三种使用方式
- 支持 **fast / balanced / high_quality** 压缩模式
- 支持 **auto / python / ghostscript** 压缩后端
- 文本型 PDF 快速路径优化
- 图像型 PDF 智能压缩
- 支持大文件自动分段
- SQLite 持久化任务记录
- WebSocket 实时进度推送
- 提供 benchmark 性能对比脚本

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动 Web 服务

```bash
python app.py
```

打开浏览器访问：

```text
http://localhost:5000
```

### 启动 GUI

```bash
python main.py
```

### CLI 压缩

```bash
python main.py --cli input.pdf
python main.py --cli input.pdf -o output.pdf -t 200
```

## 环境要求

- Python 3.10+
- Windows / Linux / macOS
- 可选：Ghostscript（推荐，用于更快压缩图像型 PDF）

## Ghostscript（可选）

如需启用 Ghostscript，请先安装 Ghostscript，并在 `config.yaml` 中配置路径：

```yaml
compression:
  ghostscript_path: "C:\\Program Files\\gs\\gs10.03.1\\bin\\gswin64c.exe"
```

## 配置

默认配置文件：`config.yaml`

推荐默认值：

```yaml
compression:
  target_size_mb: 200
  default_quality: 85
  mode: "balanced"
  backend: "auto"
```

## Benchmark

对同一个 PDF 做性能对比：

```bash
python benchmark.py input.pdf
python benchmark.py input.pdf --target 200 --quality 85
```

默认会对比：

- fast + auto
- fast + ghostscript
- balanced + auto
- balanced + python

## 推荐策略

### 优先速度
- 模式：`fast`
- 后端：`ghostscript`

### 平衡效果与稳定性
- 模式：`balanced`
- 后端：`auto`

### 更看重质量
- 模式：`high_quality`
- 后端：`auto`

## 项目结构

```text
PDFTool/
├── app.py
├── main.py
├── benchmark.py
├── config.yaml
├── requirements.txt
├── src/
│   ├── core/
│   ├── database/
│   ├── gui/
│   ├── utils/
│   └── websocket_manager.py
├── static/
├── templates/
└── tests/
```

## 测试

```bash
python tests\test_basic.py
```

## 开源说明

建议不要提交以下运行时文件：

- `uploads/`
- `outputs/`
- `data/tasks.db`
- `__pycache__/`
- `.idea/`

项目已包含 `.gitignore`。

## License

MIT
