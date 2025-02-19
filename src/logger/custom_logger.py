import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from logger.config import LoggerConfig


class ColoredFormatter(logging.Formatter):
    """A custom logging formatter that adds ANSI color codes to log level names.

    This formatter enhances log messages by inserting color codes around the log level
    names based on their severity. This is especially useful for console outputs where
    visual cues can help in quickly identifying log messages of different levels.
    """

    COLORS = {
        "DEBUG": "\033[92m",  # Green
        "INFO": "\033[94m",  # Blue
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: Any) -> str:
        """Format the log record by adding color to the log level name.

        Args:
            record (Any): The log record to be formatted.

        Returns:
            str: The formatted log message with the colored log level name.
        """
        levelname = record.levelname
        # Remove any stray reset codes and then get the proper color.
        levelname_stripped = levelname.strip(self.RESET)
        log_color = self.COLORS.get(levelname_stripped, self.RESET)
        record.levelname_colored = f"{log_color}{levelname_stripped}{self.RESET}"
        return super().format(record)


class CustomLogger(logging.Logger):
    """CustomLogger is a subclass of logging.Logger that configures itself using a Pydantic LoggerConfig.

    This logger loads its configuration from environment variables via the LoggerConfig model,
    which validates settings such as log directory, log level, verbosity, and file rotation parameters.
    It then attaches a console handler (with color-coded log levels) and a rotating file handler to itself.

    Args:
        name (str): The name of the logger instance.
    """

    def __init__(self, name: str, cfg: LoggerConfig) -> None:

        # Convert the log level string (already validated) to its numeric value.
        self.log_level = logging._nameToLevel.get(cfg.log_level, logging.INFO)
        # Create the log file path using the current date and time.
        self.log_file = cfg.log_dir / f"{datetime.now():%Y-%m-%d_%H%M%S}.log"
        self.verbose = cfg.log_verbose
        self.max_bytes = cfg.max_bytes
        self.backup_count = cfg.backup_count

        # Initialize the base Logger with the proper level.
        super().__init__(name, level=self.log_level)

        # Set up the console and file handlers on this logger instance.
        self._setup_logging()

        # Prevent log messages from propagating to the root logger (avoids duplicates).
        self.propagate = False

    def _setup_logging(self) -> None:
        """Configure this logger with console and rotating file handlers."""
        # Formatter for console logs (with colors).
        console_formatter = ColoredFormatter(
            "%(asctime)s [%(levelname_colored)s] %(name)s:%(lineno)d: %(message)s"
        )
        # Standard formatter for file logs.
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
        )

        # Create and configure the console handler.
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(console_formatter)

        # Create and configure the rotating file handler.
        file_handler = RotatingFileHandler(
            filename=str(self.log_file),
            mode="a",
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(file_formatter)

        # Attach the handlers to this logger instance.
        self.addHandler(console_handler)
        self.addHandler(file_handler)
