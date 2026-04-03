# PDFTool

[简体中文](./README.zh-CN.md) | English

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

PDFTool is an open-source PDF compression toolkit with **Web**, **GUI**, and **CLI** entry points.  
It supports multiple compression modes, optional Ghostscript acceleration, automatic splitting for oversized outputs, and task persistence for web workflows.

## Feature Matrix

| Capability | Web | GUI | CLI |
|---|---|---|---|
| Upload/compress/download | Yes | Yes | Yes |
| Compression modes (`fast` / `balanced` / `high_quality`) | Yes | Yes | Yes |
| Backend selection (`auto` / `python` / `ghostscript`) | Yes | Yes | Yes |
| Auto split oversized results | Yes | Yes | Yes |
| Real-time progress | Yes (WebSocket + polling fallback) | Yes | Yes |
| Task persistence | Yes (SQLite) | No | No |

## Requirements

- Python 3.10+
- Windows / Linux / macOS
- Optional: Ghostscript (recommended for faster image-heavy PDF compression)

## Install

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Run Web server

```bash
python app.py
```

Then open `http://localhost:5000`.

### 2. Run GUI

```bash
python main.py
```

### 3. Run CLI

```bash
python main.py --cli input.pdf
python main.py --cli input.pdf -o output.pdf -t 200
```

## Configuration

Default config file: `config.yaml`

```yaml
compression:
  target_size_mb: 200
  default_quality: 85
  mode: "fast"           # fast | balanced | high_quality
  backend: "auto"        # auto | python | ghostscript
  ghostscript_path: ""   # optional absolute path
```

## Runtime Environment Variables (Web)

- `PDFTOOL_DEBUG`: enable Flask debug mode (`false` by default)
- `PDFTOOL_HOST`: bind host (`0.0.0.0` by default)
- `PDFTOOL_PORT`: bind port (`5000` by default)

Example:

```bash
PDFTOOL_DEBUG=true PDFTOOL_HOST=127.0.0.1 PDFTOOL_PORT=8080 python app.py
```

## Optional Ghostscript Setup

If Ghostscript is installed, you can explicitly set its executable path in `config.yaml`:

```yaml
compression:
  ghostscript_path: "C:\\Program Files\\gs\\gs10.03.1\\bin\\gswin64c.exe"
```

## Test

```bash
python tests/test_basic.py
```

## FAQ

### Why does `auto` backend still use Python?
`auto` tries Ghostscript first only when it is available and considered beneficial for current content. Otherwise it falls back to Python rendering.

### Why can output still be larger than target?
Some PDFs (mixed vector/text content, embedded fonts, or high-complexity pages) have compression limits. The splitter can generate multiple files when a single file cannot hit the target safely.

## Known Limits

- Extremely malformed/encrypted PDFs may fail validation or compression.
- Different Ghostscript versions may produce slightly different size/quality trade-offs.

## Security

Please report vulnerabilities via `SECURITY.md`.

## Changelog

See `CHANGELOG.md`.

## License

MIT License.
