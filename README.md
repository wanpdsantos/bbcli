# bbcli - Bitbucket Command Line Interface

A powerful and intuitive command-line interface for interacting with the Bitbucket API. Manage projects, repositories, users, and branch permissions with ease.

## Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install bbcli

1. Clone the repository:

   ```bash
   git clone <repository_url>
   cd bbcli
   ```

2. Run the installation:
   ```bash
   make install
   ```

This will:

- Create a virtual environment in `~/.bbcli/env`
- Install bbcli and its dependencies
- Create a symlink in `~/.local/bin/bbcli`

### Verify Installation

```bash
bbcli --version
bbcli --help
```

## Quick Start

### 1. Authentication

bbcli supports OAuth 2.0 (recommended) and App Password authentication:

#### OAuth 2.0 (Recommended)

```bash
# One-time setup: Configure OAuth app
bbcli oauth setup --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET

# Authenticate (opens browser)
bbcli auth login
```

To create an OAuth app:

1. Go to `Bitbucket Workspace Settings`
2. In the left sidebar, over the Apps and Features section, Click "OAuth Consumers" tab → "Add consumer"
3. Add a name and set callback URL to `http://localhost:8080/callback`
4. Grant required permissions (Account, Repositories, Projects, etc.)
5. After you create you will be given a Key and a Secret that you will use in the `bbcli oauth setup` command. The Key is the Client ID and the Secret is the Client Secret.

#### App Password (Alternative)

```bash
bbcli auth login-basic
```

You'll need to create a Bitbucket App Password with the following permissions:

- Projects: Read, Write, Admin
- Repositories: Read, Write, Admin
- Account: Read
- Pull Requests: Read, Write
- Branching: Read, Write

### 2. Create a Project

```bash
bbcli project create MYPROJ --name "My Project" --workspace myworkspace
```

### 3. Create a Repository

```bash
bbcli repo create my-app --project MYPROJ --workspace myworkspace
```

### 4. Add a User to Repository

```bash
bbcli repo user add my-app --project MYPROJ --user user@example.com --permission write --workspace myworkspace
```

### 5. Configure Branch Permissions

```bash
bbcli branch permission exempt-pr my-app --project MYPROJ --user {account-id} --workspace myworkspace
```

## Usage

### Authentication Commands

#### OAuth 2.0 Commands

```bash
# Set up OAuth app credentials
bbcli oauth setup --client-id YOUR_ID --client-secret YOUR_SECRET

# Authenticate with OAuth (opens browser)
bbcli auth login

# Check OAuth status
bbcli oauth status

# Remove OAuth data
bbcli oauth logout
```

#### Basic Auth Commands

```bash
# Set up app password authentication
bbcli auth login-basic

# Check authentication status (shows both OAuth and Basic Auth)
bbcli auth status

# Remove stored credentials
bbcli auth logout
```

### Project Commands

```bash
# Create a project
bbcli project create PROJECTKEY --name "Project Name" --workspace myworkspace

# List projects in workspace
bbcli project list --workspace myworkspace

# Show project details
bbcli project show PROJECTKEY --workspace myworkspace
```

### Repository Commands

```bash
# Create a repository
bbcli repo create repo-name --project PROJECTKEY --workspace myworkspace

# Add user to repository
bbcli repo user add repo-name --project PROJECTKEY --user user@example.com --permission write --workspace myworkspace

# Remove user from repository
bbcli repo user remove repo-name --project PROJECTKEY --user user@example.com --workspace myworkspace
```

### Branch Permission Commands

```bash
# Exempt user from pull request requirement
bbcli branch permission exempt-pr repo-name --project PROJECTKEY --user {account-id} --workspace myworkspace

# Enforce pull request requirement for user
bbcli branch permission enforce-pr repo-name --project PROJECTKEY --user {account-id} --workspace myworkspace
```

### Global Options

- `--help`, `-h`: Show help information
- `--version`, `-v`: Show version
- `--verbose`: Enable verbose output
- `--output`, `-o`: Output format (`text`, `json`, `yaml`)

## Development

### Setup Development Environment

#### Option 1: Using Makefile (Recommended)

```bash
make install-dev
```

This will:

- Install development dependencies
- Set up pre-commit hooks
- Configure the development environment

#### Option 2: Using uv directly

```bash
# Clone the repository
git clone https://github.com/your-username/bbcli.git
cd bbcli

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --dev

# Set up pre-commit hooks
uv run pre-commit install
```

### Code Quality and Pre-commit Hooks

This project uses pre-commit hooks to maintain code quality and consistency. The hooks automatically run before each commit to:

- **Format and lint code** with Ruff
- **Sort imports** with isort
- **Check types** with mypy
- **Run tests** with pytest
- **Validate files** (YAML, TOML, etc.)

#### Running Pre-commit Manually

```bash
# Run all hooks on all files
uv run pre-commit run --all-files

# Run specific hooks
uv run pre-commit run ruff --all-files
uv run pre-commit run ruff-format --all-files
uv run pre-commit run mypy --all-files
```

#### Skipping Hooks (Not Recommended)

```bash
# Skip all hooks
git commit --no-verify

# Skip specific hooks
SKIP=pytest git commit -m "your message"
SKIP=mypy,pytest git commit -m "your message"
```

#### MyPy Error Analysis

Use the provided script to analyze and get suggestions for fixing mypy errors:

```bash
# Analyze mypy errors and get suggestions
uv run python scripts/fix-mypy-errors.py

# Run mypy manually for detailed output
uv run mypy src/ --config-file=pyproject.toml
```

The script provides:

- **Error summary** by type and count
- **Specific suggestions** for common error patterns
- **File-by-file breakdown** of errors
- **Next steps** for gradual type improvement

### Running Tests

```bash
# Using Makefile
make test
make test-cov
make lint
make format
make check

# Using uv directly
uv run pytest
uv run pytest --cov=bbcli
uv run ruff check .
uv run ruff format .
uv run isort .
uv run mypy src/
```

### Building

```bash
# Using Makefile
make build

# Using uv directly
uv build
```

## Configuration

bbcli stores configuration in `~/.bbcli/`:

- `config.yaml` - User preferences and settings
- `credentials.enc` - Encrypted credentials (fallback storage)

### Configuration Options

```yaml
default_workspace: myworkspace
default_output_format: text
api:
  base_url: https://api.bitbucket.org/2.0
  timeout: 30
  max_retries: 3
ui:
  show_progress: true
  confirm_destructive: true
  color: true
```

## Security

- **OAuth 2.0**: Modern, secure authentication with PKCE support
- **Secure Token Storage**: OAuth tokens and credentials stored using system keyring when available
- **Encrypted Fallback**: Local storage with AES-256 encryption when keyring unavailable
- **HTTPS Only**: All API communications use HTTPS
- **Token Expiration**: Automatic handling of token expiration and refresh
- **Privacy**: Sensitive data is masked in verbose output

## Troubleshooting

### Authentication Issues

#### OAuth 2.0 Issues

1. **"OAuth app not configured"**: Run `bbcli oauth setup` with your OAuth app credentials
2. **"No authorization code received"**: Check redirect URI matches your OAuth app configuration
3. **"Token expired"**: Run `bbcli auth login` to re-authenticate
4. **Browser doesn't open**: Use `--no-browser` flag and manually open the authorization URL

#### App Password Issues

1. Ensure your App Password has the required permissions
2. Check that your username is correct (not email)
3. Verify the App Password hasn't expired

### Permission Errors

1. Verify you have the necessary permissions in the workspace/project
2. Check that the workspace/project/repository exists
3. Ensure you're using the correct workspace identifier

### API Errors

1. Check your internet connection
2. Verify the Bitbucket API is accessible
3. Check for rate limiting (wait and retry)

## Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Set up the development environment**:
   ```bash
   git clone https://github.com/your-username/bbcli.git
   cd bbcli
   uv sync --dev
   uv run pre-commit install
   ```
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes**
5. **Add tests** for new functionality
6. **Run the test suite**:
   ```bash
   uv run pytest
   ```
7. **Ensure code quality** (pre-commit hooks will run automatically):
   ```bash
   uv run pre-commit run --all-files
   ```
8. **Commit your changes** (pre-commit hooks will run):
   ```bash
   git add .
   git commit -m "Add your feature description"
   ```
9. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
10. **Submit a pull request**

### Code Quality Standards

- All code must pass the pre-commit hooks (formatting, linting, type checking)
- New features must include tests
- Tests must pass with good coverage
- Follow the existing code style and patterns
- Add docstrings for new public functions and classes
