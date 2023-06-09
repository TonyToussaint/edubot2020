import discord
from discord.ext.commands import Bot
from discord.ext import commands
import asyncio

@has_permissions(manage_messages=True, read_message_history=True)
@bot_has_permissions(manage_messages=True, read_message_history=True)
@commands.group(name="clear")
async def clear(ctx, limit: int = 100, user: discord.Bot, *, matches: str = None):
    logger.info('clear', extra={'ctx': ctx})
    def check_msg(msg):
        if msg.id == ctx.message.id:
            return True
        if user is not None:
            if msg.author.id != user.id:
                return False
        if matches is not None:
            if matches not in msg.content:
                return False
        return True
    deleted = await ctx.channel.clear(limit=limit, check=check_msg)
    msg = await ctx.send(i18n(ctx, 'clear', len(deleted)))
    await a.sleep(2)
    await msg.clear()