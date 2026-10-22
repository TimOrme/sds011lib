# Compile client code
build: install_deps

# Install dependencies for project
install_deps:
    uv sync --no-install-project

# Lint code.
lint:
    uv run ruff format --check .
    uv run ruff check .
    uv run mypy . --strict

tox:
    uv run tox -e py

# Format code
format:
    uv run ruff format .

# Run tests
test:
    uv run pytest tests/