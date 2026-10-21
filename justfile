# Compile client code
build: install_deps

# Install dependencies for project
install_deps:
    uv sync --no-install-project

# Lint code.
lint:
    uv run black --check .
    uv run ruff check .
    uv run mypy . --strict

# Format code
format:
    uv run black .

# Run tests
test:
    uv run pytest tests/