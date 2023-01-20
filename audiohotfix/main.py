import asyncio
import contextlib

from redbot.core.bot import Red
from redbot.core.commands import commands
from redbot import VersionInfo, version_info


class AudioHotFix(commands.Cog):

    def __init__(self, bot: Red):
        self.bot = bot
        if version_info >= VersionInfo.from_str("3.5.0.dev294"):
            raise EnvironmentError("The fix which this cog implements is already in Red")
        if version_info < VersionInfo.from_str("3.5.0.dev0"):
            # I CBA to look for the exact commit which changed this,
            #   there is a change of folks using an old dev build where the attribute name
            #   hasn't been changed over to managed_node_controller yet
            self.attribute_name = "player_manager"
        else:
            self.attribute_name = "managed_node_controller"
        self.loop = None
        self.monitor = asyncio.create_task(self.task_restart)
        self.cog_monitor_task = None
        self.buffer_exit = False

    async def loop_for_cog(self):
        while not (__:= self.bot.get_cog("Audio")):
            await asyncio.sleep(1)
        if self.loop is not None:
            self.loop = asyncio.create_task(self.read_buffer)
        while (__:= self.bot.get_cog("Audio")):
            await asyncio.sleep(1)
            if self.buffer_exit is True:
                if self.loop is not None:
                    self.loop.cancel()
                self.loop = asyncio.create_task(self.read_buffer)
        self.loop = None


    async def read_buffer(self):
        self.buffer_exit = False
        while True:
            with contextlib.suppress(Exception):
                cog = self.bot.get_cog("Audio")
                attribute = getattr(cog, self.attribute_name, None)
                if attribute is None or attribute._proc is None:
                    self.buffer_exit = True
                    return
                async for __ in attribute._proc.stdout:
                    pass
        self.buffer_exit = True

    async def task_restart(self):
        while True:
            if self.cog_monitor_task is None:
                await self.bot.wait_until_red_ready()
                self.cog_monitor_task = asyncio.create_task(self.loop_for_cog)
            await asyncio.sleep(1)

    def cog_unload(self):
        self.monitor.cancel()
        if self.loop is not None and not self.loop.cancelled():
            self.loop.cancel()
        if self.cog_monitor_task is not None and not self.cog_monitor_task.cancelled():
            self.cog_monitor_task.cancel()
