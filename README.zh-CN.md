# PDFTool

简体中文 | [English](./README.md)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

PDFTool 是一个开源 PDF 压缩工具包，提供 **Web**、**GUI**、**CLI** 三种使用方式。支持多种压缩模式、可选 Ghostscript 加速、超大文件自动分段，以及 Web 场景下的任务持久化。

## 功能矩阵

| 能力 | Web | GUI | CLI |
|---|---|---|---|
| 上传/压缩/下载 | 支持 | 支持 | 支持 |
| 压缩模式（`fast` / `balanced` / `high_quality`） | 支持 | 支持 | 支持 |
| 后端选择（`auto` / `python` / `ghostscript`） | 支持 | 支持 | 支持 |
| 超限自动分段 | 支持 | 支持 | 支持 |
| 实时进度 | WebSocket + 轮询兜底 | 信号驱动 | 标准输出 |
| 任务持久化 | SQLite | 不支持 | 不支持 |

## 环境要求

- Python 3.10+
- Windows / Linux / macOS
- 可选：Ghostscript（图像型 PDF 通常压缩更快）

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

### Web 服务

```bash
python app.py
```

浏览器访问 `http://localhost:5000`。

### GUI

```bash
python main.py
```

### CLI

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

split:
  enabled: true
  max_size_mb: 200

output:
  suffix: "_compressed"
  segment_suffix: "_part"
  keep_original: true
```

## 环境变量（Web）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `PDFTOOL_DEBUG` | `false` | 是否开启调试模式 |
| `PDFTOOL_HOST` | `0.0.0.0` | 绑定地址 |
| `PDFTOOL_PORT` | `5000` | 绑定端口 |

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

当 `backend` 设为 `auto` 时，工具会优先尝试 Ghostscript 处理图像密集型 PDF；若 Ghostscript 不可用或压缩效果不足，则自动回退到 Python 渲染流程。

## 项目结构

```
PDFTool/
├── app.py                  # Flask Web 服务入口
├── main.py                 # GUI / CLI 入口
├── benchmark.py            # 性能基准测试工具
├── config.yaml             # 默认配置
├── requirements.txt        # Python 依赖
├── src/
│   ├── core/
│   │   ├── compressor.py   # 压缩引擎
│   │   ├── analyzer.py     # PDF 分析
│   │   ├── image_processor.py  # 图像压缩
│   │   └── splitter.py     # 文件分段
│   ├── database/
│   │   └── task_db.py      # SQLite 任务持久化
│   ├── gui/
│   │   ├── main_window.py  # PyQt5 主窗口
│   │   ├── widgets.py      # 自定义控件
│   │   └── styles.py       # UI 样式
│   ├── utils/
│   │   ├── config.py       # 配置加载
│   │   ├── file_utils.py   # 文件工具
│   │   └── logger.py       # 日志
│   └── websocket_manager.py # WebSocket 进度推送
├── templates/
│   └── index.html          # Web 前端
├── static/
│   └── js/enhanced.js      # WebSocket 与预设 UI
└── tests/
    └── test_basic.py       # 基础测试
```

## 测试

```bash
python tests/test_basic.py
```

## 常见问题

**为什么 `auto` 后端有时还是用 Python？**
`auto` 会优先尝试 Ghostscript，但仅在可用且对当前 PDF 预期有效时启用；否则自动回退到 Python 流程。

**为什么结果可能仍大于目标大小？**
部分 PDF（复杂矢量、字体嵌入、混合内容）压缩空间有限，系统会在必要时走分段输出以保证可用性。

## 已知限制

- 对于损坏或特殊加密 PDF，可能出现校验或压缩失败。
- 不同 Ghostscript 版本在体积与清晰度上可能有细微差异。

## 安全说明

安全漏洞请参考 [SECURITY.md](./SECURITY.md) 进行反馈。

## 许可证

[MIT License](./LICENSE)。
