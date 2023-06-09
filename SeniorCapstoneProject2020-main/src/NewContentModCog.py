# discord imports
import discord
from discord.ext import commands
from discord.ext.commands.cog import Cog

# EduBot imports
import EduBotChecks
import EduBotExceptions
import NewBotCache

# other imports
import re
from typing import Union, Optional
import json
import validators
from better_profanity import profanity
profanity.load_censor_words()


class ContentModeration(commands.Cog, name="Content Moderation"):
    """Cog contains methods and listeners for content moderation features including
    mass message deletion and automatic message filtering
    """

    def __init__(self, bot: commands.Bot, cache: NewBotCache.Cache):
        self.bot = bot
        self.cache = cache
        self.unlockHandles = {}
        self.data_from_url_check = []

    #### LISTENERS #####################################################################################
    # listener used to load restricted urls file
    @Cog.listener()
    async def on_ready(self):
        with open('../data/urlCheck.json') as f:
            self.data_from_url_check = json.load(f)

    # Listener used to scan for language filter infractions in newly sent messages
    @Cog.listener()
    async def on_message(self, message):
        channel = await self.cache.getServerInfractionChannelID(message.guild.id)
        if(channel == None):
            pass
        else:
            channel = self.bot.get_channel(channel)
            await self.urlFilter(message, channel, message.channel)

            if(message.author != self.bot.user):
                if(profanity.contains_profanity(message.content)):
                    if(message.content[0] == await self.cache.getServerCommandPrefix(message.guild.id)):
                        return
                    else:
                        InfractionReport = "\n==================================\nLanguage Infraction Noted:\nLocation: {}\nUser Name: {}\nNickname: {}\nMessage Content: {}".format(message.channel,message.author, message.author.nick, message.content)
                        try:
                            await message.delete()
                        except Exception:
                            return  
                        await channel.send(InfractionReport)       
            
    # Listener used to scan for language filter infractions in formerly clean but newly edited
    @Cog.listener()
    async def on_message_edit(self, beforeModification, afterModification):
        channel = await self.cache.getServerInfractionChannelID(afterModification.guild.id)
        if(channel == None):
            pass
        else:
            channel = self.bot.get_channel(channel)
            await self.urlFilter(afterModification, channel, afterModification.channel)

            if(afterModification.author != self.bot.user):
                if(profanity.contains_profanity(afterModification.content)):
                    channel = await self.cache.getServerInfractionChannelID(afterModification.guild.id)
                    channel = self.bot.get_channel(channel)
                    await channel.send("\n==================================\n")
                    await channel.send("Language Infraction Noted:\nLocation: {}\nUser Name: {}\nNickname: {}\nMessage Content: {}".format(afterModification.channel,afterModification.author, afterModification.author.nick, afterModification.content))
                    await afterModification.delete()

    # Listener used to delete command invoke messages on successful command execute
    @Cog.listener()
    async def on_command_completion(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass



    #### COMMANDS ######################################################################################
    ## Infraction Channel Command ##
    @commands.command(name="InfractionChannelSet", brief="Allows for Infraction Channel to be set.", usage = "[new infraction channel name]", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def InfractionChannelSetting(self, ctx, newChannel: discord.TextChannel):
        ''' Sets a new channel as the place infraction reports will go to.'''
        if isinstance(newChannel, discord.TextChannel):        
            await self.cache.setServerInfractionChannelID(ctx.guild.id, newChannel.id)
        else:
            raise commands.BadArgument

    
    @InfractionChannelSetting.error
    async def InfractionChannelSettingError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send("Error: There is no channel under this name. Please enter an existing channel.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    ## Notification Channel Command ##
    @commands.command(name="NotificationChannelSet", brief="Allows for Notification Channel to be set.", usage = "[new Notification channel name]", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def NotificationChannelSetting(self, ctx, newChannel: discord.TextChannel):
        ''' Sets a new channel as the place notifications will go to.'''
        if isinstance(newChannel, discord.TextChannel):        
            await self.cache.setServerNotificationChannelID(ctx.guild.id, newChannel.id)
        else:
            raise commands.BadArgument

    @NotificationChannelSetting.error
    async def NotificationChannelSettingError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send("Error: There is no channel under this name. Please enter an existing channel.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    #### Mass Message Deletion ####
    @commands.group(name="deleteMSG", brief="Parent command for mass message deletion.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def deleteMSG(self, ctx):
        """Parent command for mass message deletion. Allows for the deletion of all existing messages 
        for a user or role, all existing messages, or some number of recent messages from the channel 
        the command is run in.
        """
        if(ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for deleteMSG command. Use help deleteMSG for more information.")

    @deleteMSG.error
    async def deleteMSGError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @deleteMSG.command(name="user", brief="Delete specific user's messages in channel.", usage="user")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def deleteMSGUser(self, ctx, user: Union[discord.Member, str]):
        """Deletes all messages sent by the given user from the channel the command is run in.
        """
        if(isinstance(user, str)):
            if("*" in user):
                pattern = user
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")
                nameMatch = lambda name: (re.fullmatch(pattern, name.name) is not None) or (re.fullmatch(pattern, str(name.nick)) is not None)
                results = list(filter(nameMatch, ctx.guild.members))

                if (len(results) == 0):
                    raise EduBotExceptions.NoMembersMatchedPattern(user)

                if(not results):
                    await ctx.send("This user does not exist, or the wildcard did not have any results.")
                
                else:
                    for result in results:
                        def UserCheck(message: discord.Message):
                            return result == message.author
                        await ctx.channel.purge(check=UserCheck)
                        await ctx.send("{}'s Messages Deleted.".format(result))
        else:

            if(user not in ctx.guild.members):
                raise commands.errors.BadArgument
            else:
                def UserCheck(message: discord.Message):
                    return user == message.author
                await ctx.channel.purge(check=UserCheck)
                await ctx.send("{}'s Messages Deleted.".format(user))

    @deleteMSGUser.error
    async def DeleteUser_error(self, ctx, error):
        # Runs when there is no user by given name
        if isinstance(error, commands.BadArgument):
            await ctx.send("Error: User does not exist in server!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")  


    @deleteMSG.command(name="role", brief="Delete specific role's messages in channel.", usage="role")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def deleteMSGRole(self, ctx, role: Union[discord.Role, str]):
        """Deletes all messages sent by any users with the given role from the channel the command is run in.
        """
        if(isinstance(role, str)):

            if("*" in role):                
                pattern = role
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")
                nameMatch = lambda name: re.fullmatch(pattern, name.name) is not None
                results = list(filter(nameMatch, ctx.guild.roles))

                if (len(results) == 0):
                    raise EduBotExceptions.NoRolesMatchedPattern(role)

                for result in results:

                    def authorHasRole(message: discord.Message):
                        return result in message.author.roles
                    await ctx.channel.purge(check=authorHasRole)
                    await ctx.send("{}'s Messages Deleted.".format(result))
        else:

            # Checks to see if role exists in server
            if(role not in ctx.guild.roles):
                raise commands.errors.BadArgument
            def authorHasRole(message: discord.Message):
                return role in message.author.roles
            await ctx.channel.purge(check=authorHasRole)
            await ctx.send("{} Role Messsages Deleted.".format(role))

    @deleteMSGRole.error
    async def DeleteRole_error(self, ctx, error):
        # Runs when there is no user by given name
        if isinstance(error, commands.BadArgument):
            await ctx.send("Error: Role does not exist in the server!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")  


    @deleteMSG.command(name="all", breif="Deletes all messages in channel.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def deleteMSGAll(self, ctx):
        """Deletes all messages in channel that the command is run in."""
        # Gets guild id
        guild = ctx.guild.id
        # Clones Channel
        cloneChannel = await ctx.channel.clone()
        await cloneChannel.edit(position=ctx.channel.position)
        cloneChannelID = cloneChannel.id
        originalChannelID = ctx.channel.id

        # updates db
        await self.cache.updateOverwriteChannel(guild, originalChannelID, cloneChannelID)

        # Check if infraction or notification channel
        if(originalChannelID == await self.cache.getServerInfractionChannelID(guild)):
            # Update's infraction channel ID
            await self.cache.setServerInfractionChannelID(guild, cloneChannelID)
        if(originalChannelID == await self.cache.getServerNotificationChannelID(guild)):
            #update's notification channel IP
            await self.cache.setServerNotificationChannelID(guild, cloneChannelID)

        # deletes original channel
        await ctx.channel.delete()


    @deleteMSG.command(name="amount", brief="Deletes a given number of oldest messages.", usage="amountToDelete")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def deleteMSGAmount(self, ctx, amountToDelete: int):
        """Deletes the given number of messages from the channel the command is run in, starting with 
        oldest messages in the channel.
        """
        if(amountToDelete <= 0):
            raise commands.errors.BadArgument
        else:
            await ctx.channel.purge(oldest_first = True, limit=amountToDelete)
            await ctx.send("Messages Deleted.")

    @deleteMSGAmount.error
    async def DeleteAmount_error(self, ctx, error):
        # Runs when there is no user by given name
        if isinstance(error, commands.BadArgument):
            await ctx.send("Error: Must be positive number!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")



    #### HELPER METHODS ################################################################################
    def validateUrl(self, url):
        '''validates if the message sent is an url or not
        '''
        try:
            validators.url(url)
            return url
        except:
            pass

    def image_filter(self, message):
        pic_extension = ['jpg', 'png', 'gif']
        message_attachments = message.attachments
        for attachments in message_attachments:
            if attachments.filename[-3:] in pic_extension:
                return True
            else:
                return

    async def urlFilter(self, message, infraction_channel, message_channel):
        '''make sure the websites posted on the server are not NSFW
        '''
        #check if the message is image or not
        message_is_image = self.image_filter(message)
        message_is_url = self.validateUrl(message.content)
        url_info = self.data_from_url_check['url']
        if message_is_image == None:
            for url_dict in url_info:
                if (message_is_url in url_dict['link']):
                    await message.delete()
                    await message_channel.send(f"This link sent is NSFW!!!")
                    await infraction_channel.send("\n==================================\n")
                    await infraction_channel.send(f"Link Infraction Noted:\nLocation: {message.channel}\nUser Name: {message.author}\nType: {url_dict['type']}\nThreat: {url_dict['threat']}\nLink sent: <{message.content}>")

        else:
            return
