# PDFTool

[简体中文](./README.zh-CN.md) | English

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

PDFTool is an open-source PDF compression toolkit with **Web**, **GUI**, and **CLI** interfaces. It supports multiple compression modes, optional Ghostscript acceleration, automatic splitting for oversized outputs, and task persistence for web workflows.

## Features

| Capability | Web | GUI | CLI |
|---|---|---|---|
| Upload / compress / download | Yes | Yes | Yes |
| Compression modes (`fast` / `balanced` / `high_quality`) | Yes | Yes | Yes |
| Backend selection (`auto` / `python` / `ghostscript`) | Yes | Yes | Yes |
| Auto split oversized results | Yes | Yes | Yes |
| Real-time progress | WebSocket + polling fallback | Signal-based | Stdout |
| Task persistence | SQLite | No | No |

## Requirements

- Python 3.10+
- Windows / Linux / macOS
- Optional: Ghostscript (recommended for faster image-heavy PDF compression)

## Install

```bash
pip install -r requirements.txt
```

## Quick Start

### Web Server

```bash
python app.py
```

Open `http://localhost:5000` in a browser.

### GUI

```bash
python main.py
```

### CLI

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
  ghostscript_path: ""   # optional absolute path to Ghostscript executable

split:
  enabled: true
  max_size_mb: 200

output:
  suffix: "_compressed"
  segment_suffix: "_part"
  keep_original: true
```

## Environment Variables (Web)

| Variable | Default | Description |
|---|---|---|
| `PDFTOOL_DEBUG` | `false` | Enable Flask debug mode |
| `PDFTOOL_HOST` | `0.0.0.0` | Bind host |
| `PDFTOOL_PORT` | `5000` | Bind port |

Example:

```bash
PDFTOOL_DEBUG=true PDFTOOL_HOST=127.0.0.1 PDFTOOL_PORT=8080 python app.py
```

## Ghostscript (Optional)

If Ghostscript is installed, set its path in `config.yaml`:

```yaml
compression:
  ghostscript_path: "C:\\Program Files\\gs\\gs10.03.1\\bin\\gswin64c.exe"
```

When `backend` is `auto`, the tool will try Ghostscript first for image-heavy PDFs and fall back to Python rendering when Ghostscript is unavailable or yields insufficient compression.

## Project Structure

```
PDFTool/
├── app.py                  # Flask web server entry point
├── main.py                 # GUI / CLI entry point
├── benchmark.py            # Performance benchmarking utility
├── config.yaml             # Default configuration
├── requirements.txt        # Python dependencies
├── src/
│   ├── core/
│   │   ├── compressor.py   # Compression engine
│   │   ├── analyzer.py     # PDF analysis
│   │   └── splitter.py     # File splitting
│   ├── database/
│   │   └── task_db.py      # SQLite task persistence
│   ├── gui/
│   │   ├── main_window.py  # PyQt5 main window
│   │   ├── widgets.py      # Custom widgets
│   │   └── styles.py       # UI styles
│   ├── utils/
│   │   ├── config.py       # Configuration loader
│   │   ├── file_utils.py   # File utilities
│   │   └── logger.py       # Logging
│   └── websocket_manager.py # WebSocket progress push
├── templates/
│   └── index.html          # Web frontend
├── static/
│   └── js/enhanced.js      # WebSocket & preset UI
└── tests/
    └── test_basic.py       # Basic tests
```

## Test

```bash
python tests/test_basic.py
```

## FAQ

**Why does `auto` backend still use Python?**
`auto` tries Ghostscript first only when it is available and considered beneficial for the current PDF content. Otherwise it falls back to Python rendering.

**Why can output still be larger than target?**
Some PDFs (mixed vector/text content, embedded fonts, high-complexity pages) have compression limits. The splitter can generate multiple files when a single file cannot safely reach the target size.

## Known Limits

- Extremely malformed or encrypted PDFs may fail validation or compression.
- Different Ghostscript versions may produce slightly different size/quality trade-offs.

## Security

Please report vulnerabilities via [SECURITY.md](./SECURITY.md).

## License

[MIT License](./LICENSE).
