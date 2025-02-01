import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from colorama import Fore, Style, init
from logging.handlers import TimedRotatingFileHandler

init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """
    Custom logging formatter to add colors to the log output.
    """

    def __init__(self, fmt: str, datefmt: str = "%Y-%m-%d %H:%M:%S") -> None:
        super().__init__(fmt, datefmt)  # inherit default formatter
        self.level_colors = {
            logging.DEBUG: Fore.BLUE,
            logging.INFO: Fore.GREEN,
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.MAGENTA,
        }
        self.time_color = Fore.GREEN + Style.DIM

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats a log record with color-coded level and timestamp.

        This method customizes the log record format by adding colors to the
        log level name and timestamp.

        Args:
            record (logging.LogRecord): The log record to be formatted.

        Returns:
            str: The formatted log message with color-coded elements.
        """

        level_color = self.level_colors.get(record.levelno, Fore.WHITE)

        colored_time = (
            self.time_color + self.formatTime(record, self.datefmt) + Style.RESET_ALL
        )

        levelname = record.levelname.ljust(8)[:8]
        colored_levelname = level_color + levelname + Style.RESET_ALL

        # replace original asctime and levelname format
        fmt_original = self._style._fmt

        self._style._fmt = fmt_original.replace("%(asctime)s", colored_time)
        self._style._fmt = self._style._fmt.replace(
            "%(levelname)-8s", colored_levelname
        )

        formatted_message = super().format(record)

        self._style._fmt = fmt_original

        return formatted_message


class LoggerConfig:
    """
    LoggerConfig setup the global logger
    """

    def __init__(
        self,
        log_level: int = logging.INFO,
        log_dir: str = "logs",
        log_to_file: bool = True,
        log_to_stderr: bool = True,
        timezone: float = 0,
    ) -> None:
        self.logger = logging.getLogger()
        self.logger.setLevel(log_level)
        self.logger.propagate = False
        self.timezone = timezone

        # remove all default handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # custom log format
        self.log_format = (
            "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
        )

        if log_to_stderr:
            self._add_stream_handler()

        if log_to_file:
            self._add_file_handler(log_dir)

    def _add_stream_handler(self) -> None:
        """
        Adds a StreamHandler to the logger to log messages to stderr.
        It uses ColoredFormatter to add colors to the log output.

        Returns:
            None
        """
        stream_handler = logging.StreamHandler(sys.stderr)
        colored_formatter = ColoredFormatter(
            self.log_format, datefmt="%Y-%m-%d %H:%M:%S%z"
        )
        stream_handler.setFormatter(colored_formatter)
        self.logger.addHandler(stream_handler)

    def _add_file_handler(self, log_dir: str) -> None:
        """
        Adds a FileHandler to the logger to log messages to a file in the specified directory.

        Args:
            log_dir: The directory where log files will be stored. If the directory
                        does not exist, it will be created.

        Returns:
            None
        """

        Path(log_dir).mkdir(parents=True, exist_ok=True)
        timefmt = (
            datetime.now(timezone.utc)
            .astimezone(timezone(timedelta(hours=self.timezone)))
            .strftime("%Y%m%d_%H-%M-%S%z")
        )
        log_filename = Path(log_dir) / f"{timefmt}.log"

        file_handler = TimedRotatingFileHandler(
            filename=log_filename,
            when="d",
            interval=1,
            backupCount=30,
            encoding="utf-8",
            delay=True,
        )

        # file log will use plain formatter to keep log readable
        plain_formatter = logging.Formatter(
            self.log_format, datefmt="%Y-%m-%d %H:%M:%S(%z)"
        )
        file_handler.setFormatter(plain_formatter)
        self.logger.addHandler(file_handler)

    def get_logger(self, name: str = None) -> logging.Logger:
        """
        get a formatted logger instance

        :param name: logger name, default is None
        :return: logging.Logger instance
        """
        if name:
            return logging.getLogger(name)
        return self.logger


class AppLog:
    def __init__(
        self, name: str = None, log_level: int = logging.INFO, timezone: float = 0
    ) -> None:
        """
        Initializes the AppLog object.

        :param name: logger name, default is None
        :param log_level: logging level, default is logging.INFO

        :return: None
        """
        self._debug_interupt_code = 99
        self._error_exit_code = -1

        default_logger_config = LoggerConfig(
            log_level=log_level, log_dir="logs", timezone=timezone
        )
        self._logger = default_logger_config.get_logger(name)

    def debug(self, message: str, with_interupt: bool = False) -> None:
        """
        Logs a debug message.

        Args:
            message: The debug message to log.
            with_interupt: If True, the program will exit with a 99 exit code.

        Returns:
            None
        """
        self._logger.debug(message, stacklevel=2)

        if with_interupt:
            sys.exit(self._debug_interupt_code)

    def info(self, message: str) -> None:
        """
        Logs a info message.

        Args:
            message: The debug message to log.

        Returns:
            None
        """
        self._logger.info(message, stacklevel=2)

    def warning(self, message: str) -> None:
        """
        Logs a warning message.

        Args:
            message: The debug message to log.

        Returns:
            None
        """
        self._logger.warning(message, stacklevel=2)

    def error(self, message: str, with_interupt: bool = False) -> None:
        """
        Logs a error message.

        Args:
            message: The debug message to log.
            with_interupt: If True, the program will exit with a non-zero exit code.

        Returns:
            None
        """
        self._logger.error(message, stacklevel=2)

        if with_interupt:
            sys.exit(self._error_exit_code)

    def critical(self, message: str) -> None:
        """
        Logs a critical message.

        **Note:** This method will exit the program with a non-zero exit code.

        Args:
            message: The debug message to log.

        Returns:
            None
        """
        self._logger.critical(message, stacklevel=2)
        sys.exit(self._error_exit_code)
