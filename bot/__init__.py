import asyncio
import logging
import os
import sys
from functools import partial, partialmethod
from logging import Logger, handlers
from pathlib import Path
from typing import TYPE_CHECKING

import coloredlogs
from discord.ext import commands

from bot.command import Command

if TYPE_CHECKING:
    from bot.bot import Bot

TRACE_LEVEL = logging.TRACE = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def monkeypatch_trace(self: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log 'msg % args' with severity 'TRACE'.

    To pass exception information, use the keyword argument exc_info with
    a true value, e.g.

    logger.trace("Houston, we have an %s", "interesting problem", exc_info=1)
    """
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, msg, args, **kwargs)


Logger.trace = monkeypatch_trace

DEBUG_MODE = 'local' in os.environ.get("SITE_URL", "local")

log_level = TRACE_LEVEL if DEBUG_MODE else logging.INFO
format_string = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
log_format = logging.Formatter(format_string)

log_file = Path("logs", "bot.log")
log_file.parent.mkdir(exist_ok=True)
file_handler = handlers.RotatingFileHandler(log_file, maxBytes=5242880, backupCount=7, encoding="utf8")
file_handler.setFormatter(log_format)

root_log = logging.getLogger()
root_log.setLevel(log_level)
root_log.addHandler(file_handler)

if "COLOREDLOGS_LEVEL_STYLES" not in os.environ:
    coloredlogs.DEFAULT_LEVEL_STYLES = {
        **coloredlogs.DEFAULT_LEVEL_STYLES,
        "trace": {"color": 246},
        "critical": {"background": "red"},
        "debug": coloredlogs.DEFAULT_LEVEL_STYLES["info"]
    }

if "COLOREDLOGS_LOG_FORMAT" not in os.environ:
    coloredlogs.DEFAULT_LOG_FORMAT = format_string

if "COLOREDLOGS_LOG_LEVEL" not in os.environ:
    coloredlogs.DEFAULT_LOG_LEVEL = log_level

coloredlogs.install(logger=root_log, stream=sys.stdout)

logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("chardet").setLevel(logging.WARNING)
logging.getLogger(__name__)


# On Windows, the selector event loop is required for aiodns.
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Monkey-patch discord.py decorators to use the Command subclass which supports root aliases.
# Must be patched before any cogs are added.
commands.command = partial(commands.command, cls=Command)
commands.GroupMixin.command = partialmethod(commands.GroupMixin.command, cls=Command)

instance: "Bot" = None  # Global Bot instance.
