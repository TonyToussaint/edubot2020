import NewBotCache
import EduBotChecks
# from ServerAdminCog import ServerAdministration
# from ContentModCog import ContentModeration
from NotificationSysCog import NotificationSystem
from NewServerAdminCog import ServerAdministration
from NewContentModCog import ContentModeration
from EduBotFeaturesCog import EduBotFeatures
from ReactionsCog import Reactions 
import discord
from discord.ext import commands
import asyncio

# method returns the prefix for the bot associated with the server the message was sent on
async def get_prefix(client, message):
    prefix = await cache.getServerCommandPrefix(message.guild.id)
    return prefix

# establishes bot's command prefix, which will differentiate commands from regular
# messages; and sets bots intents, which allows it access to certain server information
botIntents = discord.Intents.all()
bot = commands.Bot(command_prefix=get_prefix, intents=botIntents, case_insensitive = True)


#### LISTENERS ####

# Listener used to add a servers database entry when bot is invited
# to a new server
@bot.listen()
async def on_guild_join(guild):
    await cache.addServer(guild.id)

# Listener used to remove servers database entry when bot is removed
# from a server
@bot.listen()
async def on_guild_remove(guild):
    await cache.remServer(guild.id)

# Listener used to remove polls and permOverwrites from database when
# a channel is deleted
@bot.listen()
async def on_guild_channel_delete(channel):
    await cache.prunePolls(channel.guild.id, channel.id)
    #TODO: this will erroneously delete entries if a channel was cleared while server locked unless
    # channel is deleted only after updateOverwriteChannel is called
    await cache.remPermOverwrite(channel.guild.id, channel.id) 

# Listener used to remove entries in permOverwrite table for users that
# have left the server
@bot.listen()
async def on_member_remove(member):
    await cache.remPermOverwrite(member.guild.id, modifiedID=member.id)


#### COMMANDS ####
@bot.command(name="editCommandPrefix", brief="Sets the command prefix for this server.", usage="newPrefix")
@commands.check(EduBotChecks.hasElevatedPrivileges)
async def changePrefix(ctx, newPrefix):
    """Allows the user to change the single-character command prefix that the bot will use to distinguish 
    normal messages from command messages.
    """
    # restrict length of prefix to one character
    if (len(newPrefix) == 1):
        await cache.setServerCommandPrefix(ctx.guild.id, newPrefix)
    else:
        raise commands.errors.BadArgument
    await ctx.send(f"The command prefix for this server is now {newPrefix}.")

@changePrefix.error
async def changePrefixError(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(f"Error: Missing argument for 'newPrefix'!")
    elif isinstance(error, commands.errors.BadArgument):
        await ctx.send(f"Error: newPrefix must be a single character argument!")
    else:
        await ctx.send(f"An unhandled exception occured: {error}")

# General Error Handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("The command you entered was not recognized! Use command 'help' for a list of available commands!")


#### MAIN ####
# create Cache object from BotCache
cache = NewBotCache.Cache("../data/LocalCache.db")
EduBotChecks.setCacheReference(cache)

# add cogs to bot
bot.add_cog(ServerAdministration(bot, cache))
bot.add_cog(ContentModeration(bot, cache))
bot.add_cog(NotificationSystem(bot, cache))
bot.add_cog(EduBotFeatures(bot, cache))
# bot.add_cog(Reactions(bot))

# start periodic commit loop
cache.saveDBToFile.start()

try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.start("Nzk4MzQ0MjA2OTQxNjgzNzUz.X_zp-w.KNEbvC4eJJU4E8xyby9OJ_XTPnE"))
except KeyboardInterrupt:
    loop.run_until_complete(bot.logout)
finally:
    loop.run_until_complete(cache.saveDBToFile())
    loop.close()