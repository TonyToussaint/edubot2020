# discord imports
import discord
from discord.ext import commands

# EduBot imports
import NewBotCache
import EduBotChecks
import EduBotExceptions

# other imports
import asyncio
import re
import warnings
from typing import Union, Optional
from sqlite3 import IntegrityError
from random import shuffle

class EduBotFeatures(commands.Cog, name="EduBot Features"):
    def __init__(self, bot: commands.Bot, cache: NewBotCache.Cache):
        self.bot = bot
        self.cache = cache
        self.managedDeletions = set()

    #### LISTENERS #####################################################################################
    # Will check joining users to see if they used a role invite
    @commands.Cog.listener()
    async def on_member_join(self, member):
        commandRestrictionChannel = discord.utils.get(member.guild.channels, name='notifications')
        channel_id = commandRestrictionChannel.id
        channel = self.bot.get_channel(channel_id)
        embed = discord.Embed(title=f"Welcome to the server {member.name}", description=None, color=0x0000FF)
        await channel.send(embed=embed)
        after_join = await member.guild.invites()
        role_id_for_link = await self.cache.roleIDFromUsedLink(member.guild.id, after_join)
        get_role = discord.utils.get(channel.guild.roles, id=int(role_id_for_link))
        await member.add_roles(get_role)
        await channel.send(f'{member} has been given the role {get_role}')
    
    # Server Initial Configuration
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        category_list = guild.categories
        #checks and sees if there are any categories already in the server
        if not category_list:
            category_text = await guild.create_category('Text Channels')
            category_voice = await guild.create_category('Voice Channels')
            await guild.create_text_channel('notifications',\
                                            overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True, connect=False, send_messages=False, view_channel=True)}, \
                                            category=category_text,\
                                            reason=None)
            await guild.create_text_channel('admin-only',\
                                            overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False)},\
                                            category=category_text,\
                                            reason=None)
            await guild.create_text_channel('student', overwrites=None, category=category_text, reason=None)
            await guild.create_voice_channel('student', overwrites=None, category=category_voice, reason=None)
        #if there are categories, are they text or voice categories, if not create them and create channels under them. If already exist then just create channels
        else:
            for category in category_list:
                if category.name == 'Text Channels':
                    await guild.create_text_channel('notifications', \
                                                    overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True, connect=False, send_messages=False, view_channel=True)}, \
                                                    category=category, \
                                                    reason=None)
                    await guild.create_text_channel('Infraction Channel', \
                                                    overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False)}, \
                                                    category=category, \
                                                    reason=None)
                    await guild.create_text_channel('admin-only', \
                                                    overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False)}, \
                                                    category=category, \
                                                     reason=None)
                    await guild.create_text_channel('student', overwrites=None, category=category, reason=None)

                elif category.name == 'Voice Channels':
                    await guild.create_voice_channel('student', overwrites=None, category=category, reason=None)

                else:
                    category_text = await guild.create_category('Text Channels')
                    category_voice = await guild.create_category('Voice Channels')
                    await guild.create_text_channel('notifications', \
                                                    overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True, connect=False, send_messages=False, view_channel=True)}, \
                                                    category=category_text, \
                                                    reason=None)
                    await guild.create_text_channel('Infraction Channel', \
                                                    overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False)}, \
                                                    category=category_text, \
                                                    reason=None)
                    await guild.create_text_channel('admin-only', \
                                                    overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False)}, \
                                                    category=category_text, \
                                                    reason=None)
                    await guild.create_text_channel('student', overwrites=None, category=category_text, reason=None)
                    await guild.create_voice_channel('student', overwrites=None, category=category_voice, reason=None)
        #let the server owner know that initial configuration has been setup
        commandRestrictionChannel = discord.utils.get(guild.channels, name='notifications')
        infractionChannel = discord.utils.get(guild.channels, name = "Infraction Channel")
        await self.cache.setServerInfractionChannelID(guild.id, infractionChannel)
        channel_to_send = self.bot.get_channel(commandRestrictionChannel.id)
        message = "The server has been set up with the predefined initial configuration"
        embed = discord.Embed(title="Initial Server Configuration", description=message, color=0x00FF00)
        embed.set_footer(text="Announcement made by EduBot")
        await channel_to_send.send(embed=embed)

        return

    # Will clean cache after deleting server roles
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        if (role.id not in self.managedDeletions):
            await self.cache.remGroupRole(role.guild.id, role.id)
            await self.cache.remPrivilegedRole(role.guild.id, role.id)
            await self.cache.remExcludedRole(role.guild.id, role.id)
        await self.cache.remPermOverwrite(role.guild.id, modifiedID=role.id)



    #### COMMANDS ######################################################################################
    #### Auto-Grouping Commands ####
    @commands.group(name="group", brief="Parent command for group commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def group(self, ctx):
        """Parent command for all group related commands, including creation, deletion, and renaming commands.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for group command. Use help group for more information.")

    @group.error
    async def group_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @group.group(name="create", brief="Parent command for group creation commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def createGroups(self, ctx):
        """Parent command for all group creation related commands, including random group generation and manual group
        creation.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for group create. Use help group create for more information.")

    @createGroups.error
    async def createGroups_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @createGroups.command(name="manual", brief="Creates a group with the given name and members.", usage="nameOfGroup [memberToAdd...]", ignore_extra=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def createGroupsManual(self, ctx, nameOfGroup: str, membersToGroup: commands.Greedy[discord.Member]):
        """Creates a user group and the channels associated with the group with the provided name and
        list of server members to add to the group. Members are specified in a space seperated list, and
        can be given by either a username, username + discriminator, nickname, or mention. If no members
        are passed then group will be created with no members.
        """

        # create role and channels for group
        groupRole = await ctx.guild.create_role(name=nameOfGroup, hoist=True, mentionable=True)
        groupCategory = await ctx.guild.create_category(name=nameOfGroup, overwrites={
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False),
            groupRole: discord.PermissionOverwrite(read_messages=True, connect=True, view_channel=True)
        })
        await ctx.guild.create_text_channel(name=f"{nameOfGroup}-general".replace(" ", "-").lower(), category=groupCategory)
        await ctx.guild.create_voice_channel(name=f"{nameOfGroup} Voice", category=groupCategory)

        # add members to new group
        roleAddCoros = [member.add_roles(groupRole) for member in membersToGroup]
        await asyncio.wait(roleAddCoros)

        # add group to database
        await self.cache.addGroupRole(ctx.guild.id, groupRole.id, groupCategory.id)

        await ctx.send(f"{nameOfGroup} was created!")

    @createGroupsManual.error
    async def createGroupsManual_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.TooManyArguments):
            await ctx.send("Error: One of the provided names for membersToGroup was not a member on this server!" +\
                "\nConsider using mentions (@name) to avoid typos/ambiguities in names.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Error: membersToGroup is a required argument that is missing.")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @createGroups.command(name="random", brief="Randomly assigns students to groups.", usage="numGroups roleToGroup")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def createGroupsRandom(self, ctx, numGroups: int, roleToGroup: Union[discord.Role, str]):
        """Creates a number of groups given by numGroups, each with associated voice and text chat channels that are only
        visible to group members and administrators, then randomly assigns members to those groups. Role to group parameter
        specifies which role to group members from.
        """
        if (isinstance(roleToGroup, str)):
            raise commands.RoleNotFound(roleToGroup)
        if (numGroups <= 0):
            raise commands.BadArgument

        # build list of members belonging to roleToGroup, check if there are enough members to group, and
        # then divide them into groups
        membersToGroup = [member for member in ctx.guild.members if (not member.bot and roleToGroup in member.roles)]

        if (len(membersToGroup) >= numGroups):
            newGroups = await self.divideIntoGroups(membersToGroup, numGroups)
        else:
            raise EduBotExceptions.NotEnoughMembersError

        # build list of coroutines for bulk tasks and enter those coroutines into the event loop, using 
        # asyncio.gather if results are needed, and wait if they are not
        # create group roles
        roleCreateCoros = [ctx.guild.create_role(name=f"{(roleToGroup.name + ' ') if roleToGroup != ctx.guild.default_role else ''}Group {i+1}", hoist=True, mentionable=True)\
            for i in range(numGroups)]
        newRoles = await asyncio.gather(*roleCreateCoros)

        # add group members to roles
        assignmentCoros = []
        for role, group in zip(newRoles, newGroups):
            assignmentCoros.extend([member.add_roles(role) for member in group])
        await asyncio.wait(assignmentCoros)

        # create category channels with perms set to be private to each role
        categoryCreateCoros = [ctx.guild.create_category(name=f"{group.name}", overwrites={
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False),
            group: discord.PermissionOverwrite(read_messages=True, connect=True, view_channel=True)
        }) for group in newRoles]
        newCategories = await asyncio.gather(*categoryCreateCoros)

        # create text channels placed under categories
        textChannelCreateCoros = [ctx.guild.create_text_channel(name=f"{group.name}-general".replace(" ", "-").lower(), category=categoryChannel)\
            for group, categoryChannel in zip(newRoles, newCategories)]
        await asyncio.wait(textChannelCreateCoros)

        # create voice channels placed under categories
        voiceChannelCreateCoros = [ctx.guild.create_voice_channel(name=f"{group.name} Voice", category=categoryChannel)\
            for group, categoryChannel in zip(newRoles, newCategories)]
        await asyncio.wait(voiceChannelCreateCoros)

        # enter new roles into the cache of group roles for this server
        await self.cache.addGroupRole(ctx.guild.id, [role.id for role in newRoles], [category.id for category in newCategories])

        await ctx.send("New groups created!")
        
    @createGroupsRandom.error
    async def createGroupsRandom_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            if (error.param.name == "numGroups"):
                await ctx.send("Error: Missing argument for number of groups to create!")
        elif isinstance(error, EduBotExceptions.NotEnoughMembersError):
            await ctx.send("Error: Fewer members with specified role than groups to be made!")
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send(f"Error: Argument entered for parameter roleToGroup is not a role on this server!")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Error: Argument entered for parameter numGroups was invalid!")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("Error: You do not have permission to perform this command!")
        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, IntegrityError):
                # if this ever happens I *will* cry, don't test me
                await ctx.send("Error: Failed to cache group roles, please report error to developer!")
            else:
                await ctx.send(f"A {type(error)} error occurred: {error}")
        else:
            await ctx.send(f"A {type(error)} error occurred: {error}")


    @group.command(name="delete", brief="Delete group roles and their associated channels.", usage="{roleToDelete | 'all' | 'all-roles'}")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def deleteGroups(self, ctx, roleToDelete: Union[discord.Role, str]):
        """Deletes the group role and associated channels provided by roleToDelete. Command will only delete roles 
        created with the "group create" command. To delete all group roles, use 'group delete all' or 'group delete all-groups'.
        """

        # if roleToDelete is a string, then it failed to convert to a role, but wasn't None
        if isinstance(roleToDelete, str):
            if (roleToDelete == "all" or roleToDelete == "all-groups"):
                # create list of coroutines for deleting channels and roles and enter those coroutines
                # into the event loop
                channelDeleteCoros = []
                roleDeleteCoros = []

                serverRoleList = await self.cache.getServerGroupRolesList(ctx.guild.id)

                if (len(serverRoleList) == 0):
                    await ctx.send("There are no group roles on this server to delete!")
                    return

                for roleID in serverRoleList:
                    role = ctx.guild.get_role(roleID)
                    self.managedDeletions.add(roleID)

                    # if a roleID is left in the cache after its role is deleted, skip over it
                    if (role is None):
                        continue
                    roleDeleteCoros.append(role.delete())

                    categoryChannelID = await self.cache.getGroupCategoryChannelID(ctx.guild.id, roleID)
                    categoryChannel = ctx.guild.get_channel(categoryChannelID)
                    channelDeleteCoros.extend([channel.delete() for channel in ctx.guild.channels if (channel.category == categoryChannel)])
                    channelDeleteCoros.append(categoryChannel.delete())

                if (len(channelDeleteCoros) != 0):
                    await asyncio.wait(channelDeleteCoros)
                if (len(roleDeleteCoros) != 0):
                    await asyncio.wait(roleDeleteCoros)

                # remove roles from cache
                serverRoleList = await self.cache.getServerGroupRolesList(ctx.guild.id)
                await self.cache.remGroupRole(ctx.guild.id, serverRoleList)
                await self.cache.remPrivilegedRole(ctx.guild.id, serverRoleList)
                await self.cache.remExcludedRole(ctx.guild.id, serverRoleList)

                for roleID in serverRoleList:
                    self.managedDeletions.discard(roleID)

                await ctx.send("All group roles and associated channels deleted!")
            
            elif("*" in roleToDelete):
                pattern = roleToDelete
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")

                nameMatch = lambda role: re.fullmatch(pattern, role.name) is not None
                groupRoles = [ctx.guild.get_role(id) for id in await self.cache.getServerGroupRolesList(ctx.guild.id)]
                results = list(filter(nameMatch, groupRoles))
                if(len(results) == 0):
                    raise EduBotExceptions.NoRolesMatchedPattern(roleToDelete)

                channelDeleteCoros = []
                roleDeleteCoros = []
                rolesToRemove = []
                for result in results:
                    #TODO: Update to use category
                    # add channel delete coroutines to list
                    categoryChannelID = await self.cache.getGroupCategoryChannelID(ctx.guild.id, result.id)
                    categoryChannel = ctx.guild.get_channel(categoryChannelID)
                    channelDeleteCoros.extend([channel.delete() for channel in ctx.guild.channels if (channel.category == categoryChannel)])
                    channelDeleteCoros.append(categoryChannel.delete())

                    # add role delete coroutines to list, also add roleIDs to list to remove from cache later
                    # and to managed deletion set to avoid extraneous deletions
                    roleDeleteCoros.append(result.delete())
                    rolesToRemove.append(result.id)
                    self.managedDeletions.add(result.id)

                # run deletion coroutines
                await asyncio.wait(roleDeleteCoros)
                await asyncio.wait(channelDeleteCoros)
                await self.cache.remGroupRole(ctx.guild.id, rolesToRemove)
                await self.cache.remPrivilegedRole(ctx.guild.id, rolesToRemove)
                await self.cache.remExcludedRole(ctx.guild.id, rolesToRemove)
                for roleID in rolesToRemove:
                    self.managedDeletions.discard(roleID)

                await ctx.send(f"All groups matching pattern {roleToDelete} deleted!")
            else:
                raise commands.RoleNotFound(roleToDelete)
        elif (not await self.cache.isGroupRole(ctx.guild.id, roleToDelete.id)):
            raise EduBotExceptions.NotGroupRoleError
        else:
            #TODO: Update to use category

            # create list of coroutines for deleting channels then enter those coroutines into the event loop
            categoryChannelID = await self.cache.getGroupCategoryChannelID(ctx.guild.id, roleToDelete.id)
            categoryChannel = ctx.guild.get_channel(categoryChannelID)
            channelDeleteCoros = [channel.delete() for channel in ctx.guild.channels if (channel.category == categoryChannel)]
            channelDeleteCoros.append(categoryChannel.delete())
            await asyncio.wait(channelDeleteCoros)

            # delete roleToDelete and remove it from cache, keeping name stored for response message
            roleName = roleToDelete.name
            self.managedDeletions.add(roleToDelete.id)
            await roleToDelete.delete()
            await self.cache.remGroupRole(ctx.guild.id, roleToDelete.id)
            self.managedDeletions.discard(roleToDelete.id)
            await ctx.send(f"{roleName} and associated channels deleted!")

    @deleteGroups.error
    async def deleteGroups_error(self, ctx, error):
        if isinstance(error, commands.RoleNotFound):
            await ctx.send("Error: Group entered for 'groupToDelete' is not a role on this server!")
        elif isinstance(error, EduBotExceptions.NotGroupRoleError):
            await ctx.send("Error: Group entered for 'groupToDelete' is not a generated group role!")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("Error: You do not have permission to perform this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Error: No group role provided for deletion!")
        else:
            await ctx.send(f"A {type(error)} error occurred: {error}")


    @group.command(name="rename", brief="Renames a given group name to a given new name.", usage="groupToRename newName")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def renameGroups(self, ctx, groupToRename: discord.Role, newName: str):
        """Renames a group role given by groupToRename and the channels associated with the group role to use newName. 
        Command will only work on roles created with 'group create' command.
        """
        # check that the group being renamed is actually a generated group role for this server
        if (not await self.cache.isGroupRole(ctx.guild.id, groupToRename.id)):
            raise EduBotExceptions.NotGroupRoleError
        elif (newName == ""):
            raise commands.errors.BadArgument

        oldGroupName = groupToRename.name
        oldTextName = groupToRename.name.lower().replace(" ", "-")
        await groupToRename.edit(name=newName)

        # create list of coroutines for renaming channels then enter those coroutines into the event loop
        channelRenameCoros = []
        for channel in ctx.guild.channels:
            if (groupToRename in channel.changed_roles):
                if isinstance(channel, discord.TextChannel):
                    channelRenameCoros.append(channel.edit(name=channel.name.replace(oldTextName, newName.lower().replace(" ", "-"))))
                else:
                    channelRenameCoros.append(channel.edit(name=channel.name.replace(oldGroupName, newName)))
        await asyncio.wait(channelRenameCoros)

        await ctx.send(f"{oldGroupName} and its associated channels have been renamed!")

    @renameGroups.error
    async def renameGroups_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: Missing argument for {error.param.name}!")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error.argument} is not a role on this server!")
        elif isinstance(error, EduBotExceptions.NotGroupRoleError):
            await ctx.send("Error: Group entered for 'groupToRename' is not a generated group role!")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send("Error: New name cannot be empty!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to perform this command!")
        else:
            await ctx.send(f"A {type(error)} error occurred: {error}")



    #### User poll commands ####
    @commands.group(name="poll", brief="Parent command for poll commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def poll(self, ctx):
        """Allows for polls with unique IDs to be created, modified, and closed. Responses are based on reactions to the poll messages.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for poll. Use help poll for more information.")

    @poll.error
    async def pollError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @poll.command(name="create", brief="Creates a poll to be used.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def pollCreate(self, ctx, question, *args):
        """Creates a poll with the given question and answers. The poll's ID is printed alongside the question 
        to use when closing the poll.
        """
        sum = 0
        for a in args:
            sum += len(a) + 1
        sum += len(question)
        if sum > 1800:
            raise EduBotExceptions.PollTooLargeError
        elif len(args) > 10:
            raise EduBotExceptions.TooManyPollAnswers
        else:
            fullPoll = question
            for i in range(len(args)):
                fullPoll += f"\n({chr(65 + i)})  {args[i]}"
            msg = await ctx.send(fullPoll)
            reactions = []
            for i in range(len(args)):
                reactions.append(msg.add_reaction(chr(127462 + i)))

            pollID = await self.cache.addPoll(ctx.guild.id, msg, args)
            
            await asyncio.gather(*reactions)
            await msg.edit(content=f"Poll ID: {pollID}\n{fullPoll}")
        
    @pollCreate.error
    async def pollCreate_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: Missing required argument for {error.param}.")
        elif isinstance(error, commands.errors.CommandInvokeError):
            if isinstance(error.original, EduBotExceptions.PollTooLargeError):
                await ctx.send("Error: Poll is too large. There can be at most 1800 characters in a poll.")
            elif isinstance(error.original, EduBotExceptions.TooManyPollAnswers):
                await ctx.send("Error: Too many given poll answers. There can be at most 10 answers in a poll.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @poll.command(name="close", brief="Closes an active poll.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def pollClose(self, ctx, pollID):
        """Closes a poll with the given poll ID, provided one exists.
        """
        msg = await self.cache.retrievePoll(ctx, ctx.guild.id, pollID)
        if msg == None:
            await ctx.send(f"Error: Poll was deleted manually. Poll with ID {pollID} closed.")
            return
        count = 1
        rList = []
        answers = await self.cache.getPollQuestions(ctx.guild.id, pollID)
        for r in msg.reactions:
            if type(r.emoji) != str or len(r.emoji) > 1 or r.count == 1 or not ord(r.emoji) in range(127462, 127462 + len(answers)):
                continue
            elif r.count == count:
                rList.append(r)
            elif r.count > count:
                count = r.count
                rList = [r]
        await self.cache.remPoll(ctx.guild.id, pollID)
        result = f"Poll with ID {pollID} closed. Result:\n"
        if rList == []:
            result += "No reactions provided."
        elif len(rList) == 1:
            result += f"The answer with the most votes was {chr(ord(rList[0].emoji) - 127397)}. Answer:\n{answers[ord(rList[0].emoji) - 127462]}"
        elif len(rList) == 2:
            result += f"Tie between answers {chr(ord(rList[0].emoji) - 127397)} and {chr(ord(rList[1].emoji) - 127397)}. Answers:\n{answers[ord(rList[0].emoji) - 127462]}\n{answers[ord(rList[1].emoji) - 127462]}"
        else:
            result += "Tie between answers "
            ansStr = ""
            for i in range(len(rList) - 1):
                result += f"{chr(ord(rList[i].emoji) - 127397)}, "
                ansStr += f"\n{answers[ord(rList[i].emoji) - 127462]}"
            result += f"and {chr(ord(rList[-1].emoji) - 127397)}. Answers:" + ansStr + f"\n{answers[ord(rList[-1].emoji) - 127462]}"
        await ctx.send(result)
        
    @pollClose.error
    async def pollClose_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            if isinstance(error.original, EduBotExceptions.GuildNotInCacheError) or isinstance(error.original, EduBotExceptions.PollNotInCacheError):
                await ctx.send("Error: Poll with that ID was not found.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: Missing required argument for {error.param}.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @poll.command(name="list", brief="Lists all created polls.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def pollList(self, ctx):
        """Lists all polls created on this server along with their ID numbers.
        """
        await ctx.send("Generating list of polls...")
        sList = ["All polls:\n\n"]
        sLength = 12
        for p in await self.cache.getServerPollList(ctx.guild.id):
            msg = await self.cache.retrievePoll(ctx, ctx.guild.id, p)
            if len(msg.content) + sLength > 1998:
                await ctx.send("".join(sList))
                sList = []
                sLength = 0
            sList.append(f"{msg.content}\n\n")
            sLength += len(msg.content) + 2
        if len(await self.cache.getServerPollList(ctx.guild.id)) == 0:
            await ctx.send("No polls found.")
        else:
            await ctx.send("".join(sList))
        
    @pollList.error
    async def pollList_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            if isinstance(error.original, EduBotExceptions.GuildNotInCacheError) or isinstance(error.original, KeyError):
                await ctx.send("No polls found.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")



    #### User breakout commands ####
    @commands.group(name="breakout", brief="Parent command for breakout room commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def breakout(self, ctx):
        """Moves students into/from group channels based on existing groups created via \"!group create\". The 
        person calling the command must be in the voice channel to move students out of or to bring students to.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for breakout. Use help breakout for more information.")

    @breakout.error
    async def breakoutError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @breakout.command(name="send", brief="Sends students to breakout rooms.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def breakoutSend(self, ctx):
        """Sends students from the voice channel the admin is currently in to their group voice channels.
        """
        groupRolesList = await self.cache.getServerGroupRolesList(ctx.guild.id)
        for member in ctx.author.voice.channel.members:
            if member != ctx.author:
                for role in member.roles:
                    if role.id in groupRolesList:
                        groupCategoryID = await self.cache.getGroupCategoryChannelID(ctx.guild.id, role.id)
                        groupCategory = ctx.guild.get_channel(groupCategoryID)
                        voiceChannel = discord.utils.find(lambda channel: (channel.category == groupCategory) and (isinstance(channel, discord.VoiceChannel)), ctx.guild.channels)
                        await member.move_to(voiceChannel)
        await ctx.send("Breakout commenced.")
        
    @breakoutSend.error
    async def breakoutSend_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        elif isinstance(error, commands.errors.CommandInvokeError):
            await ctx.send("Error: Person executing the command must be within the voice channel with the students.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @breakout.command(name="return", brief="Returns students from breakout rooms.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def breakoutReturn(self, ctx):
        """Returns students from their group voice channels to the voice channel the admin is currently in.
        """
        groupRolesList = await self.cache.getServerGroupRolesList(ctx.guild.id)
        for role in groupRolesList:
            groupCategoryID = await self.cache.getGroupCategoryChannelID(ctx.guild.id, role)
            groupCategory = ctx.guild.get_channel(groupCategoryID)
            voiceChannel = discord.utils.find(lambda channel: (channel.category == groupCategory) and (isinstance(channel, discord.VoiceChannel)), ctx.guild.channels)
            for member in voiceChannel.members:
                if member != ctx.author:
                    await member.move_to(ctx.author.voice.channel)
        await ctx.send("Breakout concluded.")
        
    @breakoutReturn.error
    async def breakoutReturn_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        elif isinstance(error, commands.errors.CommandInvokeError):
            await ctx.send("Error: Person executing the command must be within a voice channel to which students will be brought.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")



    #### lock and unlock commands ####
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
            raise commands.errors.BadArgument

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
                defaultOverwrite = discord.PermissionOverwrite.from_pair(discord.Permissions.none, discord.Permissions.none)
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
        elif isinstance(error, commands.errors.BadArgument):
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



    #### HELPER METHODS ################################################################################
    async def divideIntoGroups(self, membersToGroup, numGroups):
        """Divides membersToGroup into numGroups random groups and returns it as a list 
        of member lists for each group.
        """
        # shuffle the members list and slice it into groups
        shuffle(membersToGroup)

        groupList = []
        groupSize = len(membersToGroup) // numGroups
        remainderSize = len(membersToGroup) % numGroups

        for i in range(0, len(membersToGroup)-remainderSize, groupSize):
            groupList.append(membersToGroup[i:i+groupSize])
        
        # assign remaining members to chunks
        remainingMembers = membersToGroup[-remainderSize:]
        for i in range(remainderSize):
            groupList[i].append(remainingMembers[i])

        return groupList