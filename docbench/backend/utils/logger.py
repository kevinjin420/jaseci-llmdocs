"""Logging utility with verbosity control"""
from flask import current_app


def log_info(message, min_verbosity=1):
    """Log info message if verbosity is at or above min_verbosity

    Args:
        message: Message to log
        min_verbosity: Minimum verbosity level to log (default: 1)
            1 (-v): Basic - Frontend/backend + API communication (default)
            2 (-vv): Detailed - Add batch progress and evaluation
            3 (-vvv): Debug - Add detailed debugging info
            4 (-vvvv): Full Debug - All logging
    """
    try:
        verbosity = current_app.config.get('VERBOSITY', 1)
        if verbosity >= min_verbosity:
            current_app.logger.info(message)
    except RuntimeError:
        print(f"INFO: {message}")


def log_debug(message, min_verbosity=3):
    """Log debug message if verbosity is at or above min_verbosity

    Args:
        message: Message to log
        min_verbosity: Minimum verbosity level to log (default: 3)
    """
    try:
        verbosity = current_app.config.get('VERBOSITY', 1)
        if verbosity >= min_verbosity:
            current_app.logger.debug(message)
    except RuntimeError:
        print(f"DEBUG: {message}")


def log_error(message):
    """Log error message (always shown)"""
    try:
        current_app.logger.error(message)
    except RuntimeError:
        print(f"ERROR: {message}")


def log_warning(message, min_verbosity=2):
    """Log warning message if verbosity is at or above min_verbosity

    Args:
        message: Message to log
        min_verbosity: Minimum verbosity level to log (default: 2)
    """
    try:
        verbosity = current_app.config.get('VERBOSITY', 1)
        if verbosity >= min_verbosity:
            current_app.logger.warning(message)
    except RuntimeError:
        print(f"WARNING: {message}")


def should_log(min_verbosity):
    """Check if current verbosity level meets minimum

    Args:
        min_verbosity: Minimum verbosity level required

    Returns:
        bool: True if should log at this level
    """
    try:
        verbosity = current_app.config.get('VERBOSITY', 1)
        return verbosity >= min_verbosity
    except RuntimeError:
        return True
