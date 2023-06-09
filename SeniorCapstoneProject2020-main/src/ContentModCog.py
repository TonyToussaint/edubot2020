"""Module contains cog class for Content Moderation Features"""

import asyncio
import warnings
from typing import Union, Optional
from discord.channel import CategoryChannel, TextChannel, VoiceChannel
from discord.ext.commands.cog import Cog
import EduBotChecks
import EduBotExceptions
import NewBotCache
import discord
from discord.ext import commands, timers
from discord.ext.commands import errors
import re
import json
import validators
from better_profanity import profanity
#profanity.load_censor_words_from_file("wordfilter.txt")
profanity.load_censor_words()


class ContentModeration(commands.Cog, name="Content Moderation"):
    """
    Cog contains methods and listeners for content moderation features including
    mass message deletion and automatic message filtering
    """
    
    def __init__(self, bot: commands.Bot, cache: NewBotCache.Cache):
        self.bot = bot
        self.cache = cache
        self.unlockHandles = {}
        #self.spamDictionary = {}
        self.data_from_url_check = {}
        


    #### LISTENERS #####################################################################################
    # Listener used to scan for language filter infractions in newly sent messages
    @Cog.listener()
    async def on_ready(self):
        with open('../data/urlCheck1.json') as f:
            self.data_from_url_check = json.load(f)
        return self.data_from_url_check

    @Cog.listener()
    async def on_message(self, message):
        '''calls urlFilter to check messages sent on server is url or not'''
        if not message.author.bot:
            commandRestrictionChannel = discord.utils.get(message.guild.channels, name='infraction-channel')
            channel_to_send = self.bot.get_channel(commandRestrictionChannel.id)
            await self.urlFilter(message, channel_to_send, message.channel)

        if(message.author != self.bot.user):
            if(profanity.contains_profanity(message.content)):
                channel = await self.cache.getServerInfractionChannelID(message.guild.id)
                channel = self.bot.get_channel(channel)
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
    ## mass message deletion command group ##
    @commands.group(name="deleteMSG", brief="Parent command for mass message deletion.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def deleteMSG(self, ctx):
        """Parent command for mass message deletion. Allows for the deletion of all existing messages 
        for a user or role, all existing messages, or some number of recent messages from the channel 
        the command is run in.
        """
        if(ctx.invoked_subcommand is None):
            await ctx.send("Available subcommands for deleteMSG command:\ndeleteMSG ***user*** ***[Username]***\ndeleteMSG ***role*** ***[rolename]***\ndeleteMSG ***all*** \ndeleteMSG amount ***amount***")

    @deleteMSG.error
    async def deleteMSG_error(self, ctx, error):
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
                raise errors.BadArgument
            else:
                def UserCheck(message: discord.Message):
                    return user == message.author
                await ctx.channel.purge(check=UserCheck)
                await ctx.send("{}'s Messages Deleted.".format(user))

    @deleteMSGUser.error
    async def deleteMSGUser_error(self, ctx, error):
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
                raise errors.BadArgument
            def authorHasRole(message: discord.Message):
                return role in message.author.roles
            await ctx.channel.purge(check=authorHasRole)
            await ctx.send("{} Role Messsages Deleted.".format(role))

    @deleteMSGRole.error
    async def deleteMSGRole_error(self, ctx, error):
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
            raise errors.BadArgument
        else:
            await ctx.channel.purge(oldest_first = True, limit=amountToDelete)
            await ctx.send("Messages Deleted.")

    @deleteMSGAmount.error
    async def deleteMSGAmount_error(self, ctx, error):
        # Runs when there is no user by given name
        if isinstance(error, commands.BadArgument):
            await ctx.send("Error: Must be positive number!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")
    


    ## lock and unlock commands ##
    @commands.command(name="lock", brief="Lock all channels from view for non-moderators.", usage="[timeToLock]")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def lockServer(self, ctx, time: Optional[int]):
        """Locks the server by modifying the permissions of each channel on the server to disallow roles not
        specified in the servers privileged users from viewing, posting in, or connecting to channels on the
        server. Permissions overrides for specific members are not affected by the lock. The optional parameter 
        'timeToLock' allows the user to specify, in minutes, how long to wait before automatically unlocking the server.
        """

        # validate time argument
        if (time is not None and time <= 0):
            raise errors.BadArgument

        # check if server is already locked, if the server state has not already been cached, then cache it and
        # assume server is unlocked
        isLocked = await self.cache.getServerLockStatus(ctx.guild.id)
        if (isLocked):
            raise EduBotExceptions.ServerLockError
        
        # create locked permission overwrite
        restrictedPerms = discord.PermissionOverwrite(connect=False, send_messages=False, view_channel=False)

        # iterate through guild channels and edit overwrite for each role and member that has an overwrite,
        # ignoring channels that sync their permissions to another channel, current overwrites are cached to be
        # used in unlocking later
        cacheUpdateCoros = []
        permissionUpdateCoros = []
        for channel in ctx.guild.channels:
            if (channel.permissions_synced):
                continue
            elif (len(channel.overwrites.keys()) == 0):
                # create an overwrite for @everyone if there's no overwrites on a channel
                defaultOverwrite = discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.none())
                cacheUpdateCoros.append(self.cache.addPermOverwrite(ctx.guild.id, channel.id, ctx.guild.default_role.id, defaultOverwrite))
                permissionUpdateCoros.append(channel.set_permissions(target=ctx.guild.default_role, overwrite=restrictedPerms))
            else:
                for key in channel.overwrites.keys():
                    isPrivilegedRole = await self.cache.isPrivilegedRole(ctx.guild.id, key.id)
                    if (not isPrivilegedRole):
                        cacheUpdateCoros.append(self.cache.addPermOverwrite(ctx.guild.id, channel.id, key.id, channel.overwrites[key]))
                        permissionUpdateCoros.append(channel.set_permissions(target=key, overwrite=restrictedPerms))                  

        await asyncio.wait(cacheUpdateCoros)
        await asyncio.wait(permissionUpdateCoros)
        await self.cache.setServerLockStatus(ctx.guild.id, True)
        await ctx.send("Server locked!")
        
        # schedule the execution of unlockServer if the user provided a time for the server to unlock
        if (time is not None):
            loop = asyncio.get_event_loop()
            handle = loop.call_later(time * 60, asyncio.create_task, self.unlockServer(ctx=ctx))
            self.unlockHandles[ctx.guild.id] = handle

    @lockServer.error
    async def lockServerError(self, ctx, error):
        if isinstance(error, EduBotExceptions.ServerLockError):
            await ctx.send("Error: Server is already locked!")
        elif isinstance(error, errors.BadArgument):
            await ctx.send("Error: Invalid argument given for time to unlock!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @commands.command(name="unlock", brief="Undo lock command.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def unlockServer(self, ctx):
        """Resets the permissions on each channel of the server to the values they held before
        locking the server. If a time was set by the lock command for automatically unlocking the
        server, this command will also cancel the scheduled unlock.
        """
        # check if server is already unlocked, if the server state has not already been cached, then cache it and
        # assume server is unlocked
        isLocked = await self.cache.getServerLockStatus(ctx.guild.id)
        if (not isLocked):
            raise EduBotExceptions.ServerLockError

        # iterate through guild channels and create permission overwrites, ignoring channels that
        # sync permissions to other channels
        permissionUpdateCoros = []
        for channel in ctx.guild.channels:
            if (channel.permissions_synced):
                continue
            channelOverwritesList = await self.cache.getChannelOverwritesList(ctx.guild.id, channel.id)
            for modifiedID, overwrite in channelOverwritesList:
                # try to get role matching id number given by key, if target is None, then try to get member,
                # if that also fails, then role may have been deleted while server was locked, I don't know why
                # anybody would do that but people do dumb things so whatever
                target = ctx.guild.get_role(int(modifiedID))
                if (target is None):
                    target = ctx.guild.get_member(int(modifiedID))
                if (target is None):
                    continue

                permissionUpdateCoros.append(channel.set_permissions(target=target, overwrite=overwrite))

        await asyncio.wait(permissionUpdateCoros)
        await self.cache.setServerLockStatus(ctx.guild.id, False)
        await self.cache.remPermOverwrite(ctx.guild.id)
        await ctx.send("Server unlocked!")

        # try to cancel the unlock callback for this guild and remove it from the local cache
        # if there is no key for guild in dictionary, catch the error but do nothing
        try:
            handle = self.unlockHandles.pop(ctx.guild.id)
            #TODO: See if there isn't any other way to handle this besides suppressing the warning
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                handle.cancel()
        except KeyError:
            pass

    @unlockServer.error
    async def unlockServerError(self, ctx, error):
        if isinstance(error, EduBotExceptions.ServerLockError):
            await ctx.send("Error: Server is already unlocked!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    ## mute command group ##
    @commands.group(name="mute", brief="Parent command for mute user commands.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def muteUser(self, ctx):
        """Mute parent command groups subcommands for applying text chat and voice chat mutes to individual
        users."""
        if (ctx.invoked_subcommand is None):
            await ctx.send(
                "No subcommand given for mute command!\n" +\
                    "Available subcommands:\n" +\
                        "text userToMute\n" +
                        "voice userToMute\n" +
                        "role roleToMute"
            )

    @muteUser.error
    async def muteUserError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @muteUser.command(name="text", brief="Mutes text chat for given user.", usage="userToMute")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def muteUserText(self, ctx, userToMute: Union[discord.Member, str]):
        """Restricts a user specified by userToMute from text chatting on any channel that they do not possess
        a specific channel overwrite allowing them to bypass the mute.
        """
        # try to get the server's text mute role; if one does not already exist,
        # then create a new text mute role
        textMuteRole = discord.utils.get(ctx.guild.roles, name="EduBot_TextMute")
        if (textMuteRole is None):
            textMuteRole = await self.createTextMuteRole(ctx)

        if isinstance(userToMute, str):
            if ("*" in userToMute):
                pattern = userToMute
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")

                nameMatch = lambda member: (re.fullmatch(pattern, member.name) is not None) or (re.fullmatch(pattern, str(member.nick)) is not None)
                results = list(filter(nameMatch, ctx.guild.members))
                
                if (len(results) == 0):
                    raise EduBotExceptions.NoMembersMatchedPattern(userToMute)
                serverMuteCoros = [member.add_roles(textMuteRole) for member in results]
                await asyncio.wait(serverMuteCoros)

                await ctx.send(f"Members matching pattern {userToMute} have been text muted!")
            else:
                raise commands.errors.MemberNotFound(userToMute)
        else:
            await userToMute.add_roles(textMuteRole)
            await ctx.send(f"User {userToMute.display_name} was text muted!")

    @muteUserText.error
    async def muteUserTextError(self, ctx, error):
        if isinstance(error, EduBotExceptions.NoMembersMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, discord.HTTPException):
            await ctx.send("Error: Failed to add mute role to user!")
        elif isinstance(error, discord.Forbidden):
            await ctx.send("Error: You do not have permission to add the mute role!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have a privileged role to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @muteUser.command(name="voice", brief="Mutes voice chat for a given user.", usage="userToMute")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def muteUserVoice(self, ctx, userToMute: Union[discord.Member, str]):
        """Restricts a user specified by userToMute from voice chatting on any channel that they do not possess
        a specific channel overwrite allowing them to bypass the mute.
        """
        if isinstance(userToMute, str):
            if ("*" in userToMute):
                pattern = userToMute
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")

                nameMatch = lambda member: (re.fullmatch(pattern, member.name) is not None) or (re.fullmatch(pattern, str(member.nick)) is not None)
                results = list(filter(nameMatch, ctx.guild.members))

                if (len(results) == 0):
                    raise EduBotExceptions.NoMembersMatchedPattern(userToMute)
                serverMuteCoros = [member.edit(mute=True) for member in results]
                await asyncio.wait(serverMuteCoros)

                await ctx.send(f"Members matching pattern {userToMute} have been voice muted!")
            else:
                raise commands.errors.MemberNotFound(userToMute)
        else:
            await userToMute.edit(mute=True)
            await ctx.send(f"User {userToMute.display_name} was voice muted!")

    @muteUserVoice.error
    async def muteUserVoiceError(self, ctx, error):
        if isinstance(error, EduBotExceptions.NoMembersMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, discord.HTTPException):
            await ctx.send("Error: Failed to add mute role to user!")
        elif isinstance(error, discord.Forbidden):
            await ctx.send("Error: You do not have permission to add the mute role!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have a privileged role to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @muteUser.command(name = "role", brief="Mutes text and voice chat for given role.", usage="roleToMute")
    async def muteRole(self, ctx, role):
        """Mute members based on their roles
        """
        voiceMuteRole = discord.utils.get(ctx.guild.roles, name="EduBot_VoiceMute")
        textMuteRole = discord.utils.get(ctx.guild.roles, name="EduBot_TextMute")
        if (textMuteRole is None):
            textMuteRole = await self.createTextMuteRole(ctx)
        if (voiceMuteRole is None):
            voiceMuteRole = await self.createVoiceMuteRole(ctx)
        guild= ctx.guild
        memberList= guild.members
        for members in memberList:
            for member_role in members.roles:
                if member_role.name == role:
                    await members.add_roles(textMuteRole)
                    await members.add_roles(voiceMuteRole)
        await ctx.send(f'Members with the role {role} have been muted.')



    ## unmute command group ##
    @commands.group(name="unmute", brief="Parent command for unmute user commands.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def unmuteUser(self, ctx):
        """Unmute parent command groups subcommands for removing text chat and voice chat mutes from individual
        users."""
        if (ctx.invoked_subcommand is None):
            await ctx.send(
                "No subcommand given for mute command!\n" +\
                    "Available subcommands:\n" +\
                        "!unmute text userToUnmute\n" +
                        "!unmute voice userToUnmute\n" +
                        "!unmute role roleToUnmute"
            )

    @unmuteUser.error
    async def unmuteUserError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @unmuteUser.command(name="text", brief="Unmutes text chat for a given user.", usage="userToUnmute")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def unmuteUserText(self, ctx, userToUnmute: Union[discord.Member, str]):
        """Removes restriction on user given by userToUnmute's ability to send messages on this server.
        """
        # try to get the server's text mute role; if one does not already exist,
        # then create a new text mute role
        textMuteRole = discord.utils.get(ctx.guild.roles, name="EduBot_TextMute")
        if (textMuteRole is None):
            textMuteRole = await self.createTextMuteRole(ctx)

        if isinstance(userToUnmute, str):
            if ("*" in userToUnmute):
                pattern = userToUnmute
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")

                nameMatch = lambda member: (re.fullmatch(pattern, member.name) is not None) or (re.fullmatch(pattern, str(member.nick)) is not None)
                results = list(filter(nameMatch, ctx.guild.members))

                if (len(results) == 0):
                    raise EduBotExceptions.NoMembersMatchedPattern(userToUnmute)
                serverUnmuteCoros = [member.remove_roles(textMuteRole) for member in results]
                await asyncio.wait(serverUnmuteCoros)

                await ctx.send(f"Members matching pattern {userToUnmute} have been unmuted!")
            else:
                raise commands.errors.MemberNotFound(userToUnmute)
        else:
            await userToUnmute.remove_roles(textMuteRole)
            await ctx.send(f"User {userToUnmute.display_name} was unmuted!")

    @unmuteUserText.error
    async def unmuteUserTextError(self, ctx, error):
        if isinstance(error, EduBotExceptions.NoMembersMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, discord.HTTPException):
            await ctx.send("Error: Failed to remove mute role from user!")
        elif isinstance(error, discord.Forbidden):
            await ctx.send("Error: You do not have permission to remove the mute role!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have a privileged role to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @unmuteUser.command(name="voice", brief="Unmutes voice chat for a given user.", usage="userToUnmute")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def unmuteUserVoice(self, ctx, userToUnmute: Union[discord.Member, str]):
        """Removes restriction on user given by userToUnmute's ability to speak on this server.
        """
        if isinstance(userToUnmute, str):
            if ("*" in userToUnmute):
                pattern = userToUnmute
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")
                
                nameMatch = lambda member: (re.fullmatch(pattern, member.name) is not None) or (re.fullmatch(pattern, str(member.nick)) is not None)
                results = list(filter(nameMatch, ctx.guild.members))

                if (len(results) == 0):
                    raise EduBotExceptions.NoMembersMatchedPattern(userToUnmute)
                serverUnmuteCoros = [member.edit(mute=False) for member in results]
                await asyncio.wait(serverUnmuteCoros)

                await ctx.send(f"Members matching pattern {userToUnmute} have been unmuted!")
            else:
                raise commands.errors.MemberNotFound(userToUnmute)
        else:
            await userToUnmute.edit(mute=False)
            await ctx.send(f"User {userToUnmute.display_name} was unmuted!")

    @unmuteUserVoice.error
    async def unmuteUserVoiceError(self, ctx, error):
        if isinstance(error, EduBotExceptions.NoMembersMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, discord.HTTPException):
            await ctx.send("Error: Failed to remove mute role from user!")
        elif isinstance(error, discord.Forbidden):
            await ctx.send("Error: You do not have permission to remove the mute role!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have a privileged role to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")

  
    @unmuteUser.command(name = "role", brief="Unmutes text and voice chat for given role.", usage="roleToUnmute")
    async def unmuteRole(self, ctx, role):
        """Unmute members based on their roles
        """
        voiceMuteRole = discord.utils.get(ctx.guild.roles, name="EduBot_VoiceMute")
        textMuteRole = discord.utils.get(ctx.guild.roles, name="EduBot_TextMute")
        if (textMuteRole is None):
            textMuteRole = await self.createTextMuteRole(ctx)
        if (voiceMuteRole is None):
            voiceMuteRole = await self.createVoiceMuteRole(ctx)
        guild= ctx.guild
        memberList= guild.members
        for members in memberList:
            for member_role in members.roles:
                if member_role.name == role:
                    await members.remove_roles(textMuteRole)
                    await members.remove_roles(voiceMuteRole)
        await ctx.send(f'Members with the role {role} have been unmuted.')
    


    #### HELPER METHODS ####
    async def createTextMuteRole(self, ctx) -> discord.Role:
        """Creates a text mute role on the current server and configures the permissions overwrites of
        each channel on the server to disallow the text mute role from sending messages on the channel.
        """
        muteRole = await ctx.guild.create_role(name="EduBot_TextMute")
        permissionConfigCoros = []
        for channel in ctx.guild.channels:
            if (isinstance(channel, CategoryChannel) or isinstance(channel, TextChannel)):
                if (not channel.permissions_synced):
                    permissionConfigCoros.append(channel.set_permissions(target=muteRole, send_messages=False))
        
        await asyncio.wait(permissionConfigCoros)
        return muteRole

    async def createVoiceMuteRole(self, ctx) -> discord.Role:
        """Creates a voice mute role on the current server and configures the permissions overwrites of
        each channel on the server to disallow the voice mute role from speaking on the channel.
        """
        muteRole = await ctx.guild.create_role(name="EduBot_VoiceMute")
        permissionConfigCoros = []
        for channel in ctx.guild.channels:
            if (isinstance(channel, CategoryChannel) or isinstance(channel, VoiceChannel)):
                if (not channel.permissions_synced):
                    permissionConfigCoros.append(channel.set_permissions(target=muteRole, mute=True))
        await asyncio.wait(permissionConfigCoros)
        return muteRole

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


