.PHONY: help install install-dev uninstall clean test lint format check build dev-setup
.DEFAULT_GOAL := help

# Configuration
PYTHON := python3
UV := uv
VENV_DIR := ~/.bbcli/env
CONFIG_DIR := ~/.bbcli
INSTALL_DIR := ~/.local/bin

help: ## Show this help message
	@echo "bbcli - Bitbucket CLI Tool"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation
install: ## Install bbcli for production use
	@echo "🚀 Installing bbcli..."
	@echo "📋 Checking dependencies..."
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed. Please install Python 3.8+"; exit 1; }
	@command -v $(UV) >/dev/null 2>&1 || { echo "❌ uv is required but not installed. Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

	@echo "📁 Creating configuration directory..."
	@mkdir -p $(CONFIG_DIR)
	@chmod 700 $(CONFIG_DIR)

	@echo "🐍 Creating virtual environment..."
	@$(UV) venv $(VENV_DIR) --python $(PYTHON)

	@echo "📦 Installing bbcli..."
	@$(UV) pip install --python $(VENV_DIR)/bin/python -e .

	@echo "🔗 Creating executable symlink..."
	@mkdir -p $(INSTALL_DIR)
	@ln -sf $(VENV_DIR)/bin/bbcli $(INSTALL_DIR)/bbcli

	@echo "✅ Installation complete!"
	@echo ""
	@echo "🔧 Next steps:"
	@echo "  1. Ensure $(INSTALL_DIR) is in your PATH"
	@echo "  2. Run 'bbcli auth login' to set up authentication"
	@echo ""
	@echo "💡 If $(INSTALL_DIR) is not in your PATH, add this to your shell profile:"
	@echo "     export PATH=\"$(INSTALL_DIR):\$$PATH\""

	@echo ""
	@echo "🔐 Authentication setup:"
	@echo "  Run 'bbcli auth login' when you're ready to set up authentication"

install-dev: ## Install bbcli for development
	@echo "🛠️  Installing bbcli for development..."
	@command -v $(UV) >/dev/null 2>&1 || { echo "❌ uv is required. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

	@echo "📦 Installing development dependencies..."
	@$(UV) sync --all-extras

	@echo "🔧 Installing pre-commit hooks..."
	@$(UV) run pre-commit install

	@echo "✅ Development environment ready!"
	@echo "💡 Use 'uv run bbcli' to run the CLI in development mode"

##@ Maintenance
uninstall: ## Uninstall bbcli
	@echo "🗑️  Uninstalling bbcli..."
	@rm -f $(INSTALL_DIR)/bbcli
	@rm -rf $(VENV_DIR)
	@echo "✅ bbcli uninstalled"
	@echo "💡 Configuration directory $(CONFIG_DIR) preserved"
	@echo "    Remove manually if desired: rm -rf $(CONFIG_DIR)"

clean: ## Clean build artifacts and cache
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info/
	@rm -rf .pytest_cache/
	@rm -rf .coverage
	@rm -rf htmlcov/
	@rm -rf .mypy_cache/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"

##@ Development
dev-setup: install-dev ## Alias for install-dev

test: ## Run tests
	@echo "🧪 Running tests..."
	@$(UV) run --extra dev pytest

test-cov: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	@$(UV) run --extra dev pytest --cov-report=html
	@echo "📊 Coverage report generated in htmlcov/"

lint: ## Run linting checks
	@echo "🔍 Running linting checks..."
	@$(UV) run --extra dev ruff check src/ tests/
	@$(UV) run --extra dev mypy src/

format: ## Format code
	@echo "🎨 Formatting code..."
	@$(UV) run --extra dev ruff format src/ tests/
	@$(UV) run --extra dev isort src/ tests/

check: lint test ## Run all checks (lint + test)

##@ Build
build: ## Build distribution packages
	@echo "📦 Building distribution packages..."
	@$(UV) build
	@echo "✅ Build complete - packages in dist/"

##@ Utilities
version: ## Show version information
	@echo "bbcli version information:"
	@$(UV) run python -c "import bbcli; print(f'bbcli {bbcli.__version__}')" 2>/dev/null || echo "bbcli not installed"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "uv: $$($(UV) --version)"

deps-update: ## Update dependencies
	@echo "📦 Updating dependencies..."
	@$(UV) lock --upgrade
	@echo "✅ Dependencies updated"
