# Changelog

All notable changes to this project are documented in this file.

## v0.1.0 - Open-source Reboot (2026-04-03)

### English
- Public open-source baseline for GitHub launch.
- Added bilingual docs (`README.md` + `README.zh-CN.md`).
- Added community files: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, issue/PR templates.
- Added GitHub Actions CI for Python 3.10/3.11 on Linux.
- Web runtime now supports env vars: `PDFTOOL_DEBUG`, `PDFTOOL_HOST`, `PDFTOOL_PORT`.
- `POST /api/cleanup-old` now safely handles empty request body.
- Database schema test now uses a temporary directory to avoid repository side effects.

### 中文
- 作为 GitHub 开源首发版本建立稳定基线。
- 新增双语文档（`README.md` + `README.zh-CN.md`）。
- 新增开源协作文件：`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、`SECURITY.md`、Issue/PR 模板。
- 新增 Linux + Python 3.10/3.11 的 GitHub Actions CI。
- Web 运行新增环境变量：`PDFTOOL_DEBUG`、`PDFTOOL_HOST`、`PDFTOOL_PORT`。
- `POST /api/cleanup-old` 改为可安全处理空请求体。
- 数据库相关测试改为临时目录数据库，避免仓库目录副作用。

## v2.1.0 - Performance Optimization (2026-04-03)

- Added multithreaded page rendering strategy.
- Added smarter initial compression parameter estimation.
- Added adaptive DPI behavior by page content.

## v2.0.0 - Feature Enhancement (2026-04-03)

- Added SQLite task persistence.
- Added WebSocket real-time progress updates.
- Upgraded web UI interaction and preset controls.
- Added compression mode/backend options.
- Added rate limiting and stronger upload validation.

## v1.0.0 - Initial Version

- Initial PDF compression capability with Web/GUI/CLI entry points.
