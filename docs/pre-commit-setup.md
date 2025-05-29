# Pre-commit Setup Guide

This document provides detailed information about the pre-commit configuration for the bbcli project.

## Overview

Pre-commit hooks are automated checks that run before each commit to ensure code quality and consistency. They help catch issues early and maintain a clean, consistent codebase.

## Installed Hooks

### 1. General File Checks

- **trailing-whitespace**: Removes trailing whitespace from files
- **end-of-file-fixer**: Ensures files end with a newline
- **check-yaml**: Validates YAML file syntax
- **check-toml**: Validates TOML file syntax (pyproject.toml)
- **check-json**: Validates JSON file syntax
- **check-merge-conflict**: Detects merge conflict markers
- **check-added-large-files**: Prevents committing large files (>500KB)
- **check-ast**: Validates Python AST syntax
- **debug-statements**: Detects Python debugger imports
- **mixed-line-ending**: Fixes mixed line endings

### 2. Python Code Quality

- **Black**: Code formatting with 88-character line length
- **isort**: Import sorting compatible with Black
- **ruff**: Fast Python linter (replaces flake8)
- **mypy**: Static type checking

### 3. Testing

- **pytest**: Runs the test suite (can be skipped with `SKIP=pytest`)

## Installation

### Automatic Installation

When setting up the development environment:

```bash
uv sync --dev
uv run pre-commit install
```

### Manual Installation

If you need to install pre-commit hooks separately:

```bash
uv run pre-commit install
```

## Usage

### Automatic Execution

Pre-commit hooks run automatically when you commit:

```bash
git add .
git commit -m "Your commit message"
```

If any hook fails, the commit is blocked and you'll see output showing what was fixed or what needs to be addressed.

### Manual Execution

Run all hooks on all files:

```bash
uv run pre-commit run --all-files
```

Run specific hooks:

```bash
uv run pre-commit run black --all-files
uv run pre-commit run ruff --all-files
uv run pre-commit run mypy --all-files
uv run pre-commit run pytest --all-files
```

Run hooks on specific files:

```bash
uv run pre-commit run --files src/bbcli/core/config.py
```

### Skipping Hooks

#### Skip All Hooks (Not Recommended)

```bash
git commit --no-verify -m "Emergency commit"
```

#### Skip Specific Hooks

```bash
SKIP=pytest git commit -m "Skip tests for this commit"
SKIP=mypy,pytest git commit -m "Skip type checking and tests"
```

Available hook IDs for skipping:

- `trailing-whitespace`
- `end-of-file-fixer`
- `check-yaml`
- `check-toml`
- `check-json`
- `check-merge-conflict`
- `check-added-large-files`
- `check-ast`
- `debug-statements`
- `mixed-line-ending`
- `black`
- `isort`
- `ruff`
- `mypy`
- `pytest`

## Configuration

### Pre-commit Configuration

The main configuration is in `.pre-commit-config.yaml` at the repository root.

### Tool-Specific Configuration

Individual tools are configured in `pyproject.toml`:

- **Black**: `[tool.black]`
- **isort**: `[tool.isort]`
- **ruff**: `[tool.ruff]` and `[tool.ruff.lint]`
- **mypy**: `[tool.mypy]`
- **pytest**: `[tool.pytest.ini_options]`

## Troubleshooting

### Hook Installation Issues

If hooks aren't running:

```bash
# Reinstall hooks
uv run pre-commit uninstall
uv run pre-commit install

# Check installation
uv run pre-commit --version
```

### Hook Execution Issues

If a hook fails unexpectedly:

```bash
# Clean and reinstall environments
uv run pre-commit clean
uv run pre-commit install --install-hooks
```

### Performance Issues

If hooks are slow:

```bash
# Update to latest versions
uv run pre-commit autoupdate

# Run specific hooks only
SKIP=mypy,pytest git commit -m "Quick commit"
```

### Type Checking Issues

If mypy reports errors, here's how to handle them:

#### 1. **Missing Return Type Annotations**

```python
# Before (mypy error)
def get_user_data():
    return {"name": "John", "age": 30}

# After (fixed)
def get_user_data() -> Dict[str, Any]:
    return {"name": "John", "age": 30}
```

#### 2. **Missing Function Parameter Types**

```python
# Before (mypy error)
def process_data(data):
    return data.upper()

# After (fixed)
def process_data(data: str) -> str:
    return data.upper()
```

#### 3. **Untyped Decorators (Click CLI)**

For CLI commands using Click decorators, mypy is configured to be more lenient:

```python
# This is acceptable in CLI modules
@click.command()
@click.option("--name", help="User name")
def hello(name):  # No type annotations needed for Click commands
    click.echo(f"Hello {name}!")
```

#### 4. **Using Type Ignore Comments**

For complex cases or third-party library issues:

```python
# Use sparingly and with explanation
result = some_complex_library_function()  # type: ignore[attr-defined]
```

#### 5. **Gradual Type Adoption Strategy**

1. **Start with core modules** (config, exceptions, models)
2. **Add return types** to all functions
3. **Add parameter types** to public functions
4. **Add variable annotations** for complex types
5. **Enable stricter checks** gradually

#### 6. **Common Type Patterns**

```python
from typing import Any, Dict, List, Optional, Union

# Optional values
def get_config(key: str) -> Optional[str]:
    return config.get(key)

# Dictionary with string keys
def parse_response() -> Dict[str, Any]:
    return json.loads(response.text)

# Lists
def get_users() -> List[Dict[str, str]]:
    return [{"name": "John"}, {"name": "Jane"}]

# Union types
def process_id(user_id: Union[str, int]) -> str:
    return str(user_id)
```

#### 7. **Skipping Mypy Temporarily**

```bash
# Skip mypy for urgent commits
SKIP=mypy git commit -m "Fix types in follow-up commit"

# Run mypy manually to see all errors
uv run mypy src/ --config-file=pyproject.toml
```

### Test Failures

If pytest fails:

1. Fix the failing tests
2. Skip tests temporarily: `SKIP=pytest git commit -m "Fix tests in next commit"`
3. Run tests manually: `uv run pytest -v`

## Updating Hooks

To update all hooks to their latest versions:

```bash
uv run pre-commit autoupdate
```

This updates the hook versions in `.pre-commit-config.yaml`.

## Best Practices

1. **Run hooks manually** before committing large changes:

   ```bash
   uv run pre-commit run --all-files
   ```

2. **Fix issues incrementally** rather than skipping hooks

3. **Keep hooks updated** regularly with `pre-commit autoupdate`

4. **Don't skip hooks** unless absolutely necessary

5. **Add new hooks** as the project grows (security, documentation, etc.)

## Integration with IDEs

### VS Code

Install these extensions for better integration:

- Python
- Black Formatter
- isort
- Pylance (for type checking)
- Ruff

Configure VS Code to format on save:

```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm

1. Install the Black plugin
2. Configure Black as the formatter
3. Enable "Reformat code" and "Optimize imports" on commit
4. Configure ruff as an external tool

## Continuous Integration

The same tools used in pre-commit hooks should be run in CI/CD pipelines to ensure consistency across all environments.

Example GitHub Actions workflow:

```yaml
- name: Run pre-commit
  uses: pre-commit/action@v3.0.0
```

This ensures that all code merged into the main branch passes the same quality checks.
