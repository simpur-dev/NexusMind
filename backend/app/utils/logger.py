"""
日志配置模块
提供统一的日志管理，同时输出到控制台和文件
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOGGER_NAME = 'nexusmind'
LOG_DIR = Path(__file__).resolve().parents[2] / 'logs'
LOG_FORMAT_DETAIL = '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
LOG_FORMAT_CONSOLE = '[%(asctime)s] %(levelname)s: %(message)s'


def _ensure_utf8_stdout():
    """
    确保 stdout/stderr 使用 UTF-8 编码
    解决 Windows 控制台中文乱码问题
    """
    if sys.platform != 'win32':
        return
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')


def _formatter(fmt: str, datefmt: str) -> logging.Formatter:
    return logging.Formatter(fmt, datefmt=datefmt)


def _file_handler() -> RotatingFileHandler:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now():%Y-%m-%d}.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_formatter(LOG_FORMAT_DETAIL, '%Y-%m-%d %H:%M:%S'))
    return handler


def _console_handler() -> logging.StreamHandler:
    _ensure_utf8_stdout()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(_formatter(LOG_FORMAT_CONSOLE, '%H:%M:%S'))
    return handler


def setup_logger(name: str = DEFAULT_LOGGER_NAME, level: int = logging.DEBUG) -> logging.Logger:
    """
    设置日志器

    Args:
        name: 日志器名称
        level: 日志级别

    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        logger.addHandler(_file_handler())
        logger.addHandler(_console_handler())

    return logger


def get_logger(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    """
    获取日志器（如果不存在则创建）

    Args:
        name: 日志器名称

    Returns:
        日志器实例
    """
    logger = logging.getLogger(name)
    return logger if logger.handlers else setup_logger(name)


logger = setup_logger()


def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)
