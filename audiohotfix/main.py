from __future__ import annotations

import asyncio
import contextlib
from logging import getLogger

from redbot.cogs.audio import Audio
from redbot.cogs.audio.manager import ServerManager
from redbot.core.bot import Red
from redbot.core.commands import commands
from redbot import VersionInfo, version_info


class AudioHotFix(commands.Cog):

    def __init__(self, bot: Red):
        self.bot = bot
        self.logger = getLogger("red.3pt.audiohotfix.AudioHotFix")
        if version_info >= VersionInfo.from_str("3.5.0.dev294"):
            raise EnvironmentError("The fix which this cog implements is already in Red")
        if version_info < VersionInfo.from_str("3.5.0.dev0"):
            # I CBA to look for the exact commit which changed this,
            #   there is a change of folks using an old dev build where the attribute name
            #   hasn't been changed over to managed_node_controller yet
            self.attribute_name = "player_manager"
        else:
            self.attribute_name = "managed_node_controller"
        self.monitor = asyncio.create_task(self.task_restart())
        self.read_buffer_task = None
        self.cog_monitor_task = None
        self.buffer_exit = False

    async def loop_for_cog(self):
        try:
            while not (__ := self.bot.get_cog("Audio")):
                await asyncio.sleep(1)
            if self.read_buffer_task is not None:
                self.read_buffer_task = asyncio.create_task(self.read_buffer())
            while __ := self.bot.get_cog("Audio"):
                if self.buffer_exit is False and self.read_buffer_task is None:
                    self.read_buffer_task = asyncio.create_task(self.read_buffer())
                await asyncio.sleep(1)
                if self.buffer_exit is True:
                    if self.read_buffer_task is not None:
                        self.read_buffer_task.cancel()
                    self.read_buffer_task = asyncio.create_task(self.read_buffer())
            self.read_buffer_task = None
        except Exception as exc:
            self.logger.info("Error in loop_for_cog", exc_info=exc)

    async def read_buffer(self):
        try:
            self.buffer_exit = False
            while True:
                try:
                    cog: Audio | None = self.bot.get_cog("Audio")
                    attribute: ServerManager | None = getattr(cog, self.attribute_name, None)
                    if attribute is None or attribute._proc is None:
                        self.buffer_exit = True
                        return
                    await attribute.ready.wait()
                    with contextlib.suppress(RuntimeError):
                        async for __ in attribute._proc.stdout:
                            pass
                    self.buffer_exit = True
                    return
                except Exception as exc:
                    self.logger.info(exc, exc_info=exc)
        except Exception as exc:
            self.logger.info("Error in read_buffer", exc_info=exc)

    async def task_restart(self):
        try:
            await self.bot.wait_until_red_ready()
            while True:
                if self.cog_monitor_task is None:
                    self.cog_monitor_task = asyncio.create_task(self.loop_for_cog())
                await asyncio.sleep(1)
        except Exception as exc:
            self.logger.info("Error in task_restart", exc_info=exc)

    def cog_unload(self):
        self.monitor.cancel()
        if self.read_buffer_task is not None and not self.read_buffer_task.cancelled():
            self.read_buffer_task.cancel()
        if self.cog_monitor_task is not None and not self.cog_monitor_task.cancelled():
            self.cog_monitor_task.cancel()
