# Contributing Guide

Thanks for contributing to Ai-morphasis 2.0-2.

## Workflow

1. Create a feature branch.
2. Make focused changes.
3. Run lint and tests locally.
4. Open a pull request with a clear summary.

## Local Validation

Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest tests -v
```

Run lint:

```bash
python -m flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
```

## Guidelines

- Keep changes minimal and task-focused.
- Avoid unrelated refactors in the same PR.
- Preserve existing test behavior.
- Update docs when behavior or usage changes.

