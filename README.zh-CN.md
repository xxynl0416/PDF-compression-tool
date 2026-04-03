# PDFTool

简体中文 | [English](./README.md)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

PDFTool 是一个开源 PDF 压缩工具，提供 **Web**、**GUI**、**CLI** 三种使用方式。  
支持多种压缩模式、可选 Ghostscript 加速、超大文件自动分段，以及 Web 场景下的任务持久化。

## 功能矩阵

| 能力 | Web | GUI | CLI |
|---|---|---|---|
| 上传/压缩/下载 | 支持 | 支持 | 支持 |
| 压缩模式（`fast` / `balanced` / `high_quality`） | 支持 | 支持 | 支持 |
| 后端选择（`auto` / `python` / `ghostscript`） | 支持 | 支持 | 支持 |
| 超限自动分段 | 支持 | 支持 | 支持 |
| 实时进度 | 支持（WebSocket + 轮询兜底） | 支持 | 支持 |
| 任务持久化 | 支持（SQLite） | 不支持 | 不支持 |

## 环境要求

- Python 3.10+
- Windows / Linux / macOS
- 可选：Ghostscript（图像型 PDF 通常压缩更快）

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 启动 Web 服务

```bash
python app.py
```

浏览器访问 `http://localhost:5000`。

### 2. 启动 GUI

```bash
python main.py
```

### 3. 使用 CLI

```bash
python main.py --cli input.pdf
python main.py --cli input.pdf -o output.pdf -t 200
```

## 配置

默认配置文件：`config.yaml`

```yaml
compression:
  target_size_mb: 200
  default_quality: 85
  mode: "fast"           # fast | balanced | high_quality
  backend: "auto"        # auto | python | ghostscript
  ghostscript_path: ""   # 可选，Ghostscript 可执行文件绝对路径
```

## Web 运行环境变量

- `PDFTOOL_DEBUG`：是否开启调试模式（默认 `false`）
- `PDFTOOL_HOST`：绑定地址（默认 `0.0.0.0`）
- `PDFTOOL_PORT`：绑定端口（默认 `5000`）

示例：

```bash
PDFTOOL_DEBUG=true PDFTOOL_HOST=127.0.0.1 PDFTOOL_PORT=8080 python app.py
```

## Ghostscript（可选）

若已安装 Ghostscript，可在 `config.yaml` 中配置路径：

```yaml
compression:
  ghostscript_path: "C:\\Program Files\\gs\\gs10.03.1\\bin\\gswin64c.exe"
```

## 测试

```bash
python tests/test_basic.py
```

## 常见问题

### 为什么 `auto` 后端有时还是用 Python？
`auto` 会优先尝试 Ghostscript，但仅在可用且对当前 PDF 预期有效时启用；否则会自动回退到 Python 流程。

### 为什么结果可能仍大于目标大小？
部分 PDF（复杂矢量、字体嵌入、混合内容）压缩空间有限，系统会在必要时走分段输出以保证可用性。

## 已知限制

- 对于损坏或特殊加密 PDF，可能出现校验或压缩失败。
- 不同 Ghostscript 版本在体积与清晰度上可能有细微差异。

## 安全说明

安全漏洞请参考 `SECURITY.md` 进行反馈。

## 更新日志

见 `CHANGELOG.md`。

## 许可证

MIT License。
