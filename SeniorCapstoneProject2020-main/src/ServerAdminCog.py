"""Module contains cog class for Server Administration Features"""

import asyncio
from random import shuffle
from typing import Union, Optional
import BotCache
from sqlite3 import IntegrityError

import NewBotCache

import EduBotChecks
import EduBotExceptions
import discord
from discord.ext import commands
from discord.ext.commands.errors import BadArgument, CommandInvokeError, MissingRequiredArgument, RoleNotFound, UserNotFound
import re

def memberReturn(user: discord.Member):
    return user
def roleReturn(role: discord.Role):
    #print(role)
    return role

class ServerAdministration(commands.Cog, name="Server Administration"):
    """
    Cog contains methods and listeners for server administration features including
    kick, move, group, role, and poll commands.
    """

    def __init__(self, bot: commands.Bot, cache: NewBotCache.Cache):
        self.bot = bot
        self.cache = cache
        self.managedDeletions = set()


        # TODO: Move this into a proper storage location
        self.active_links = []
        self.invites = {}
        self.save_invites = {}
        self.connection = ""


    #### LISTENERS ####
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.invites[guild.id] = await guild.invites()

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        if (role.id not in self.managedDeletions):
            await self.cache.remGroupRole(role.guild.id, role.id)
            await self.cache.remPrivilegedRole(role.guild.id, role.id)
            await self.cache.remExcludedRole(role.guild.id, role.id)
        await self.cache.remPermOverwrite(role.guild.id, modifiedID=role.id)

    #### COMMANDS ####
    ## shutdown command ##
    @commands.command(name="shutdown", help="Shuts down the bot on command")
    @commands.check(EduBotChecks.isEduBotDev)
    async def shutdown_bot(self, ctx):
        await ctx.send("Bye Bye!")
        await ctx.bot.logout()

    ## Privileged User Commands ##
    @commands.group(name="privilegedRoles", brief="Parent command for adding and removing privileged roles.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def editAdminRoles(self, ctx):
        """Parent command for adding and removing privileged admin or moderator roles that have permission to
        execute higher level server administration bot commands.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send(
                "No subcommand given for adminRoles command!\n"\
                    + "Available subcommands:\n"\
                    + "\tadd roleToAdd"\
                    + "\tremove roleToRemove"
            )
    
    @editAdminRoles.error
    async def editAdminRolesError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    @editAdminRoles.command(name="add", brief="Add a role that can execute admin commands.", usage="roleToAdd")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def addPrivilegedRole(self, ctx, roleToAdd: Union[discord.Role, str]):
        """Adds the role specified by roleToAdd to the list of roles that can execute privileged
        commands on this server.
        """
        if(isinstance(roleToAdd, str)):
            pattern = roleToAdd
            for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                pattern = pattern.replace(i, "\\" + i)
            pattern = pattern.replace("*", ".*")
            
            nameMatch = lambda name: re.fullmatch(pattern, name.name) is not None
            results = list(filter(nameMatch, ctx.guild.roles))

            if (len(results) == 0):
                raise EduBotExceptions.NoRolesMatchedPattern(roleToAdd)

            for result in results:
                # FIXME: addPrivilegedRole supports passing a list of role ids to add, and will skip any
                # that are already in the db, this will crash part of the way through if an id is already in cache
                isPrivilegedRole = await self.cache.isPrivilegedRole(ctx.guild.id, result.id)

                if (isPrivilegedRole):
                    raise EduBotExceptions.RoleAlreadyInCache
                else:
                    await self.cache.addPrivilegedRole(ctx.guild.id, result.id)
                    await ctx.send(f"{result.name} is now a privileged role!")

        else:
            if(roleToAdd not in ctx.guild.roles):
                raise commands.errors.BadArgument
            isPrivilegedRole = await self.cache.isPrivilegedRole(ctx.guild.id, roleToAdd.id)
            if (isPrivilegedRole):
                raise EduBotExceptions.RoleAlreadyInCache
        
            await self.cache.addPrivilegedRole(ctx.guild.id, roleToAdd.id)
            await ctx.send(f"{roleToAdd.name} is now a privileged role!")

    @addPrivilegedRole.error
    async def addPrivilegedRoleError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error.argument} is not a role on this server!")
        elif isinstance(error, EduBotExceptions.RoleAlreadyInCache):
            await ctx.send("Error: Role is already a privileged role!")
        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, IntegrityError):
                # if this ever happens I *will* cry, don't test me
                await ctx.send("Error: Failed to cache group roles, please report error to developer!")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Error: This role does not exist in the server!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    @editAdminRoles.command(name="remove", brief="Remove a role that can execute admin commands.", usage="roleToRemove")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def removePrivilegedRole(self, ctx, roleToRemove: discord.Role):
        """Removes the role specified by roleToRemove from the list of roles that can execute privileged
        commands on this server.
        """

        isPrivilegedRole = await self.cache.isPrivilegedRole(ctx.guild.id, roleToRemove.id)
        if (not isPrivilegedRole):
            raise EduBotExceptions.RoleNotInCache
        
        await self.cache.remPrivilegedRole(ctx.guild.id, roleToRemove.id)
        await ctx.send(f"{roleToRemove.name} is no longer a privileged role!")

    @removePrivilegedRole.error
    async def removePrivilegedRoleError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error.argument} is not a role on this server!")
        elif isinstance(error, EduBotExceptions.RoleNotInCache):
            await ctx.send("Error: Role isn't a privileged role!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    ## Server Initial Configuration ##
    #bot will set up the server upon joining it
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



    ## Auto-Role Assigning Commands##
    # will generate link that assigns role automatically
    @commands.group(name="link", help="Generate invite links and assign roles based on the link also ", case_insensitive=True)
    @commands.check(EduBotChecks.isEduBotDev)
    async def link(self, ctx):
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand given for link command!\n" \
                           + "Available subcommands:\n" \
                           + "\tgenerate\n" \
                           + "\tlist\n"\
                           + "\tdelete **\"invite id(all if all links to be deleted)\"**\n"\
                           + "\tget **\"Role\"**\n"\
                           + "\tassign **\"Role\"** **\"invitation id\"**\n")

    @link.command(name="generate", help="generates link")
    async def generateLink(self, ctx):
        generated_link = await ctx.channel.create_invite()
        await ctx.send(f"The generated link:\n{generated_link}")

    @link.command(name="assign", help="assign link to a particular role")
    async def assign_link_role(self, ctx, role, id):
        get_role_from_name = discord.utils.get(ctx.guild.roles, name=role)
        role_id = get_role_from_name.id
        for invite in await ctx.guild.invites():
            if id == invite.id:
                await self.cache.addRoleInvite(ctx.guild.id, invite.id, role_id)
                await ctx.send(f'the link <{invite}> has been given the role generation of {role}')


    @link.command(name="list", help="returns list of links currently active")
    async def listLink(self,ctx):
        self.active_links = await ctx.guild.invites()
        if len(self.active_links) != 0:
            await ctx.send(f'**Active Link(s)**: {len(self.active_links)}\n**The Link(s)**:')
            for i in self.active_links:
                await ctx.send(f"<{i}>")
        else:
           await ctx.send("There are no active Link(s).")

    @link.command(name="get", help="returns a specific link you are looking for")
    async def get_link(self, ctx, role):
        '''get role id from the specified role name in the parameter'''
        get_role_from_name = discord.utils.get(ctx.guild.roles, name=role)
        role_id = get_role_from_name.id
        list_of_links = await self.cache.getServerRoleInvitesList(ctx.guild.id)
        for role_link in list_of_links:
            if int(role_link[1]) == role_id:
                await ctx.send(f'The link for role {role} is:\n  https://discord.gg/{role_link[0]}')

    @link.command(name="delete", help="delete all invite links")
    async def deleteListLink(self, ctx, id):
        for invite in await ctx.guild.invites():
            if invite.code == id:
                await self.bot.delete_invite(invite)
                await self.cache.remRoleInvite(ctx.guild.id, invite.code)
                await ctx.send(f'Invite link with ID {id} has been deleted.')
            elif id == "all":
                await self.bot.delete_invite(invite)
                await self.cache.remAllInvite(ctx.guild.id)
                await ctx.send("\nAll active invites have been revoked")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        commandRestrictionChannel = discord.utils.get(member.guild.channels, name='notifications')
        channel_id = commandRestrictionChannel.id
        channel = self.bot.get_channel(channel_id)
        embed = discord.Embed(title=f"Welcome to the server {member.name}", description=None, color=0x0000FF)
        await channel.send(embed=embed)
        after_join = await member.guild.invites()
        role_id_for_link = await self.cache.roleIDFromUsedLink(member.guild.id, after_join)
        get_role = discord.utils.get(member.guild.roles, id=int(role_id_for_link))
        await member.add_roles(get_role)
        await channel.send(f'{member} has been given the role {get_role}')


    ## role assignment commands
    @commands.group(name="assign", brief="Parent command for role assignment commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def assign(self, ctx):
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand given for group command!\n" \
                           + "Available subcommands:\n" \
                           + "\trole ***role to assign*** [***'member to assign'***]\n")

    @assign.error
    async def assignError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    @assign.command(name="role", brief="Assigns given role to the specified member(s).", usage="roleToAssign memberToAssign [memberToAssign...]")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def assignRoles(self, ctx, role: discord.Role=None, member: commands.Greedy[discord.Member]=None):
        """Command assigns the supplied role to the supplied space seperated list of server members. 
        Server member can be given by username, username+discriminator#, user mention (@user), or a nickname.
        """
        for people in member:
            member = people
            await member.add_roles(role)
            await ctx.send("{} Has been given the role {}".format(member, role))
        active_links = await ctx.guild.invites()
        await ctx.send("Currently active lists are {}".format(active_links))



    ## Auto-Grouping Commands ##
    @commands.group(name="group", brief="Parent command for group commands. Use help group for more info.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def group(self, ctx):
        """Parent command for all group related commands, including creation, deletion, and renaming commands."""
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand given for group command. Use help group for more information.")

    @group.error
    async def group_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    @group.group(name="create", brief="Creates user groups with voice/text channels only accessible by each group.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def createGroups(self, ctx):
        """Parent command for group creation commands"""
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for group create. Use help group create for more information.")


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
            raise BadArgument

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
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Error: Missing argument for {error.param.name}!")
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send(f"Error: {error.argument} is not a role on this server!")
        elif isinstance(error, EduBotExceptions.NotGroupRoleError):
            await ctx.send("Error: Group entered for 'groupToRename' is not a generated group role!")
        elif isinstance(error, BadArgument):
            await ctx.send("Error: New name cannot be empty!")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("Error: You do not have permission to perform this command!")
        else:
            await ctx.send(f"A {type(error)} error occurred: {error}")



    ## User Kick Commands ##
    # Kicks single user specified by argument
    @commands.group(name="kick", brief="Parent command for kick member commands.", usage = "{user | role | all}", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def kick(self, ctx):
        """Kicks either a user, role group, or every non-admin user from the server. Command will only function with those with authority."""
        if(ctx.invoked_subcommand is None):
            await ctx.send("Available subcommands for kick command:\nkick ***user*** ***[Username]***\nkick ***role*** ***[rolename]***\nkick ***all***")

    @kick.error
    async def kickError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    # Sub command kicks specified user
    @kick.command(name="user", brief="Kicks a given user.", usage = "UserName")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def kickUser(self, ctx, user: Union[discord.Member, str]):
        """Command will take a username and kick the user from the server. Will only work with those with proper authority."""
        # check to see if wildcard is given
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

                for result in results:
                    value = memberReturn(result)
                    #print(value)
                    await value.kick()
                    await ctx.send("***{} has been kicked from the server!***".format(value))
            else:
                raise commands.errors.BadArgument
    
        else:

            # Checks to see if user is in server
            if(user not in ctx.guild.members):
                raise BadArgument
            # sends notification that member has been kicked
            await ctx.send("***{} has been kicked.***".format(user))
            # kicks member
            await user.kick()

    # Error handler for kick user
    @kickUser.error
    async def KickUser_error(self, ctx, error):
        # Runs when there is no user by given name
        if isinstance(error, commands.BadArgument):
            await ctx.send("Error: User does not exist in server!")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("Error: You do not have permission to perform this command!")
        else:
            await ctx.send(f"An error has occurred: {error}")
        
    # Sub command kicks all users in group
    @kick.command(name="role", help="Kicks a given role.", usage = "[Rolename]")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def kickRole(self, ctx, role: Union[discord.Role, str]):
        """Takes a role group and kicks everyone in that group out of the server. Will only work with those with proper authority."""
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

                    #value = roleReturn(result)
                    # Stores list of people to be kicked
                    memberlist = []

                    # Adds people of the given role, and excludes bot
                    for member in ctx.guild.members:
                        if(result in member.roles and (not member.bot)):
                            memberlist.append(member)
                            #print(member)
                    
                    # Setup for for loop
                    Asgrun = []
                    for user in memberlist:
                        # Kicks every member in list
                        Asgrun.extend([user.kick()])
                        Asgrun.extend([ctx.send("***{} has been kicked.***".format(user))])
                    
                    if not Asgrun:
                        await ctx.send("Role is empty.")
                    else:
                        await asyncio.wait(Asgrun)
                    
            else:
                raise BadArgument
        else:

            # Stores list of people to be kicked
            memberlist = []

            for member in ctx.guild.members:
                if(role in member.roles and (not member.bot)):
                    memberlist.append(member)
                    #print(member)
            
            # Setup for for loop
            Asgrun = []
            for user in memberlist:
                # Kicks every member in list
                Asgrun.extend([user.kick()])
                Asgrun.extend([ctx.send("***{} has been kicked.***".format(user))])
            await asyncio.wait(Asgrun)

    # error handler for kick role
    @kickRole.error
    async def kickRole_error(self, ctx, error):
        # Runs when role does not exist
        if isinstance(error, commands.BadArgument):
            await ctx.send("Error: Role does not exist in the server!")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("Error: You do not have permission to perform this command!")
        else:
            await ctx.send(f"An error has occurred: {error}")

    # Sub command kicks all users in server
    @kick.command(name="all", help="Kicks all users excluding admins, those with the role \"Principle\", or bots.", usage = "all")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def kickall(self, ctx):
        """Kicks all non-admins from the server."""

        # Clone channel
        # Reapply webhooks
        # Update channel id in database

        
        # List to store those to kick
        memberlist = []

        # adds members into list, and excludes bot
        for member in ctx.guild.members:
            
            # Seachers for those without Principle role or bot.
            if (any(role.name == "Principle" for role in member.roles) == False and not member.bot):
                memberlist.append(member)
                print(member)
        
        # setup for for loop
        Asgrun = []
        for user in memberlist:
            # kicks all members in list
            Asgrun.extend([user.kick()])
        await asyncio.wait(Asgrun)
        # notification
        await ctx.send("All members kicked.")


    ## User move commands ##
    # move main command, if no move subcommand is provided, it will default to this
    # command, which serves only to give the command syntax for move subcommands
    @commands.group(name="move", brief="Moves a given user, role, or channel from a given voice channel to another.", usage = "{user | role | channel}", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def move(self, ctx):
        if (ctx.invoked_subcommand is None):
            """Will move user, rolegroup, or everyone from a channel into another channel"""
            await ctx.send("No subcommand given for move command!\n"\
                + "Available subcommands:\n"\
                + "\tuser **\"userToMove\"** **\"newChannel\"**\n"\
                + "\trole **\"roleToMove\"** **\"newChannel\"**\n"\
                + "\tchannel **\"channelToMove\"** **\"newChannel\"**\n")

    @move.error
    async def moveError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    # subcommand for moving a given connected user to a new channel
    @move.command(name="user", brief="Moves a given user from a given voice channel to another.", usage="[username] [newchannel]")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def moveUser(self, ctx, user: Union[discord.Member, str], channel: discord.VoiceChannel):
        """Will move user from one channel into another."""
        # check to see if wildcard is given
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

                for result in results:
                    value = memberReturn(result)
                    await value.move_to(channel)
        
        else:
            await user.move_to(channel)
        
    # error handler for the move user subcommand
    @moveUser.error
    async def moveUser_error(self, ctx, error):
        await ctx.send(error)

    # subcommand for moving all connected users with a given role to a new channel
    @move.command(name="role", brief="Moves a given role from a given voice channel to another.", usage="[roleName] [newchannel]")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def moveRole(self, ctx, role: Union[discord.Role, str], channel: discord.VoiceChannel):
        """Will move a role group in one channel into another."""
        if(isinstance(role, str)):

            if("*" in role):                
                pattern = role
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")
                nameMatch = lambda name: re.fullmatch(pattern, name.name) is not None
                results = list(filter(nameMatch, ctx.guild.roles))

                if (len(results) == 0):
                    EduBotExceptions.NoRolesMatchedPattern(role)

                for result in results:
                    doThisStuff = []
                    connectedMembers = []
                    for c in ctx.guild.channels:
                        if isinstance(c, discord.VoiceChannel):
                            connectedMembers.extend(c.members)
                    for user in result.members:
                        if user in connectedMembers:
                            doThisStuff.append(user.move_to(channel))
                    await asyncio.wait(doThisStuff)
            else:
                print("MOVE ROLE ERROR")
        else:
            #value = discord.utils.get(ctx.guild.roles, name = role)
            doThisStuff = []
            connectedMembers = []
            for c in ctx.guild.channels:
                if isinstance(c, discord.VoiceChannel):
                    connectedMembers.extend(c.members)
            for user in role.members:
                if user in connectedMembers:
                    doThisStuff.append(user.move_to(channel))
            await asyncio.wait(doThisStuff)

    # error handler for the move role subcommand
    @moveRole.error
    async def moveRole_error(self, ctx, error):
        await ctx.send(error)

    # subcommand for moving a given channel to a new channel
    @move.command(name="channel", brief="Moves a given voice channel to another.", usage = "[oldChannel] [NewChannel]")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def moveChannel(self, ctx, channelOld: discord.VoiceChannel, channelNew: discord.VoiceChannel):
        """Will move everyone in a channel into a new channel."""
        doThisStuff = []
        for user in channelOld.members:
            doThisStuff.append(user.move_to(channelNew))
        await asyncio.wait(doThisStuff)

    # error handler for the move channel subcommand
    @moveChannel.error
    async def moveChannel_error(self, ctx, error):
        await ctx.send(error)

    
    ## User poll commands ##
    # poll main command, if no poll subcommand is provided, it will default to this
    # command, which serves only to give the command syntax for poll subcommands
    @commands.group(name="poll", brief="Allows for polls with unique IDs to be created, modified, and closed. Responses are based on reactions to the poll messages.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def poll(self, ctx):
        """Allows polls to be created, modified, or closed."""
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand given for poll command!\n"\
                + "Available subcommands:\n"\
                + "\tcreate **\"question\"**\n"\
                + "\tclose **pollID**\n"\
                + "\tlist")

    @poll.error
    async def pollError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    # subcommand for creating a poll with a given question
    @poll.command(name="create", brief="Creates a poll with the given question and answers. The poll's ID is printed alongside the question to use when closing the poll.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def pollCreate(self, ctx, question, *args):
        """Creates a poll to be used."""
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
        
    # error handler for the poll create subcommand
    @pollCreate.error
    async def pollCreate_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send(f"Error: Missing required argument for {error.param}.")
        elif isinstance(error, CommandInvokeError):
            if isinstance(error.original, EduBotExceptions.PollTooLargeError):
                await ctx.send("Error: Poll is too large. There can be at most 1800 characters in a poll.")
            elif isinstance(error.original, EduBotExceptions.TooManyPollAnswers):
                await ctx.send("Error: Too many given poll answers. There can be at most 10 answers in a poll.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    # subcommand for closing a created poll
    @poll.command(name="close", brief="Closes a poll with the given poll ID, provided one exists.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def pollClose(self, ctx, pollID):
        """Closes an active poll."""
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
        
    # error handler for the poll close subcommand
    @pollClose.error
    async def pollClose_error(self, ctx, error):
        if isinstance(error, CommandInvokeError):
            if isinstance(error.original, EduBotExceptions.GuildNotInCacheError) or isinstance(error.original, EduBotExceptions.PollNotInCacheError):
                await ctx.send("Error: Poll with that ID was not found.")
        elif isinstance(error, MissingRequiredArgument):
            await ctx.send(f"Error: Missing required argument for {error.param}.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    # subcommand for listing all created polls
    @poll.command(name="list", brief="Lists all created polls.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def pollList(self, ctx):
        """Generates a list of all polls."""
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
        
    # error handler for the poll list subcommand
    @pollList.error
    async def pollList_error(self, ctx, error):
        if isinstance(error, CommandInvokeError):
            if isinstance(error.original, EduBotExceptions.GuildNotInCacheError) or isinstance(error.original, KeyError):
                await ctx.send("No polls found.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    
    ## User breakout commands ##
    # breakout main command, if no breakout subcommand is provided, it will default to this
    # command, which serves only to give the command syntax for breakout subcommands
    @commands.group(name="breakout", brief="Moves students into/from group channels based on existing groups created via \"!group create\". The person calling the command must be in the voice channel to move students out of or to bring students to.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def breakout(self, ctx):
        """Sends/returns students to/from breakout rooms."""
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand given for breakout command!\n"\
                + "Available subcommands:\n"\
                + "\tsend\n"\
                + "\treturn")

    @breakout.error
    async def breakoutError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    # subcommand for sending students to breakout rooms
    @breakout.command(name="send", brief="Sends students from the voice channel the admin is currently in to their group voice channels.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def breakoutSend(self, ctx):
        """Sends students to breakout rooms."""
        groupRolesList = await self.cache.getServerGroupRolesList(ctx.guild.id)
        for member in ctx.author.voice.channel.members:
            if member != ctx.author:
                for role in member.roles:
                    if role.id in groupRolesList:
                        for channel in ctx.guild.channels:
                            if type(channel) == discord.VoiceChannel and role in channel.overwrites.keys():
                                await member.move_to(channel)
        await ctx.send("Breakout commenced.")
        
    # error handler for the breakout send subcommand
    @breakoutSend.error
    async def breakoutSend_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        elif isinstance(error, commands.errors.CommandInvokeError):
            await ctx.send("Error: Person executing the command must be within the voice channel with the students.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    # subcommand for returning students from breakout rooms
    @breakout.command(name="return", brief="Returns students from their group voice channels to the voice channel the admin is currently in.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def breakoutReturn(self, ctx):
        """Returns students from breakout rooms."""
        groupRolesList = await self.cache.getServerGroupRolesList(ctx.guild.id)
        for channel in ctx.guild.channels:
            if type(channel) == discord.VoiceChannel:
                for role in groupRolesList:
                    for key in channel.overwrites.keys():
                        if role == key.id:
                            for member in channel.members:
                                if member != ctx.author:
                                    await member.move_to(ctx.author.voice.channel)
        await ctx.send("Breakout concluded.")
        
    # error handler for the breakout return subcommand
    @breakoutReturn.error
    async def breakoutReturn_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        elif isinstance(error, commands.errors.CommandInvokeError):
            await ctx.send("Error: Person executing the command must be within a voice channel to which students will be brought.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    # Infraction Channel Command
    @commands.command(name="InfractionChannelSet", brief="Allows for Infraction Channel to be set.", usage = "[new infraction channel name]", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def InfractionChannelSetting(self, ctx, newChannel: discord.TextChannel):
        if isinstance(newChannel, discord.TextChannel):        
            await self.cache.setServerInfractionChannelID(ctx.guild.id, newChannel.id)
        else:
            raise BadArgument

    
    @InfractionChannelSetting.error
    async def InfractionChannelSettingError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Error: You do not have permission to execute this command!")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send("Error: There is no channel under this name.")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")

    #### HELPER METHODS ####

    # method divides membersToGroup into numGroups random groups and returns
    # it as a list of member lists for each group
    async def divideIntoGroups(self, membersToGroup, numGroups):
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

            