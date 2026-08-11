"""
===============================================================================
[Design] LOGGER & CLI UI: Dual-channel file logging and clean Rich CLI output.
1. Logs detailed technical events (DEBUG/INFO) to auto-created `logs/` directory.
2. Auto-updates `.gitignore` to exclude `logs/`.
3. Provides Rich Console and Status Spinners for clean minimal terminal UI.
===============================================================================
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager
from rich.console import Console

# Shared Rich Console instance for clean terminal rendering
console = Console()

_LOGGER: Optional[logging.Logger] = None
_LOG_FILE_PATH: Optional[Path] = None


def EnsureGitIgnoreLogs():
    """Ensure `logs/` entry is present in root .gitignore."""
    gitignore_path = Path(".gitignore")
    try:
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            if "logs/" not in content and "logs\n" not in content:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write("\n# Execution Logs\nlogs/\n*.log\n")
    except Exception:
        pass


def GetLogger() -> logging.Logger:
    """Gets or initializes the global mobilerun_tester logger writing to logs/ directory."""
    global _LOGGER, _LOG_FILE_PATH

    if _LOGGER is not None:
        return _LOGGER

    EnsureGitIgnoreLogs()

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    session_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    _LOG_FILE_PATH = log_dir / f"run_{session_str}.log"

    _LOGGER = logging.getLogger("mobilerun_tester")
    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.handlers.clear()

    file_handler = logging.FileHandler(_LOG_FILE_PATH, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
    )
    file_handler.setFormatter(formatter)
    _LOGGER.addHandler(file_handler)
    _LOGGER.propagate = False

    return _LOGGER


def GetLogFilePath() -> Optional[Path]:
    """Returns the path to the current active log file."""
    return _LOG_FILE_PATH


@contextmanager
def StatusSpinner(message: str, spinner: str = "dots"):
    """
    Context manager rendering a sleek Rich terminal status spinner.
    Logs the status message to file as well.
    """
    logger = GetLogger()
    logger.info(f"[Status] {message}")
    with console.status(f"[bold cyan]{message}[/bold cyan]", spinner=spinner):
        yield
