from redbot.core.bot import Red

from audiohotfix.main import AudioHotFix


def setup(bot: Red):
    bot.add_cog(AudioHotFix(bot))