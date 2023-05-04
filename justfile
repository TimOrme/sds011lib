# Compile client code
build: install_deps

# Install dependencies for project
install_deps:
    poetry install --no-root

# Lint code.
lint:
    black --check .
    ruff check .
    mypy . --strict

# Format code
format:
    black .

# Run tests
test:
    python -m pytest tests/