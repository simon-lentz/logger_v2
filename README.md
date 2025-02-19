# Custom Logger

Custom Logger is a Python package that provides a standardized, customizable logging solution for your projects. It leverages Pydantic for configuration validation and integrates with Python's built-in logging module to deliver both colored console output and rotating file handlers.

## Features

- **Standardized Logging:** Maintain consistent logging practices across your projects.
- **Pydantic Configuration:** Ensures logger settings are validated and directories exist.
- **Rotating File Handler:** Automatically manages log file sizes and rotation.
- **Colored Console Output:** Enhances readability with ANSI color-coded log levels.
- **Easy Integration:** Import and configure in any project with minimal setup.

The entire codebase is type-checked with mypy. Additional quality measures include:

- **Testing:** Unit tests with pytest.
- **Documentation:** Docstrings in Google style.
- **Formatting:** Code formatted with Black and organized with isort.
- **CI/CD:** GitHub Actions workflows and pre-commit hooks.

## Installation

You can install the package using [Poetry](https://python-poetry.org/):

```bash
poetry install
```

Alternatively, you can build the project then install with pip:
```bash
poetry build
pip install dist/scraper-0.1.0-none-any.whl
```

## Usage

Below is an example of how to configure and use the custom logger:

```python
from pathlib import Path
from logger.config import LoggerConfig
from logger.custom_logger import CustomLogger

# Define logger configuration
config = LoggerConfig(
    log_dir=Path("/path/to/logs"),
    log_level="DEBUG",
    log_verbose=True,
    max_bytes=1048576,  # 1MB
    backup_count=3,
)

# Initialize the custom logger
logger = CustomLogger("my_custom_logger", config)

# Log messages
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.critical("This is a critical message")
```

## Configuration

The logger configuration is managed by the [`LoggerConfig`](src/logger/config.py) model. The available settings include:

- *log_dir*: Directory for storing log files (this will be created if it does not exist).
- *log_level*: Logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).
- *log_verbose*: Boolean flag to enable verbose logging.
- *max_bytes*: Maximum log file size in bytes before triggering a rotation.
- *backup_count*: Number of backup log files to retain.

If any configuration validation error occurs a `LoggerConfigError` will be raised with a descriptive message.
