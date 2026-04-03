# Contributing to PDFTool

Thanks for your interest in contributing.

## Development Setup

1. Fork and clone the repository.
2. Create a feature branch from `main`.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run basic tests:

```bash
python tests/test_basic.py
```

## Pull Request Rules

- Keep PRs focused and small.
- Describe the problem, the solution, and test evidence.
- Do not include unrelated formatting-only changes.
- Keep backward compatibility for existing API routes unless explicitly discussed.

## Commit Guidance

- Use clear commit messages (imperative mood).
- Include context in PR description rather than large commit titles.

## Testing Expectations

Before opening a PR, please verify:

- `python tests/test_basic.py` passes
- Web flow still works: upload -> compress -> download
- No runtime artifacts are committed (`uploads/`, `outputs/`, `*.db*`, temp PDFs)

## Code Style

- Follow existing code style in each module.
- Prefer readable, maintainable code over micro-optimizations.
- Add comments only when behavior is not obvious from code.

## Reporting Bugs

Please use the bug report template and include:

- Steps to reproduce
- Expected vs actual result
- Runtime environment (OS, Python version, Ghostscript version if used)
- Relevant logs/screenshots
