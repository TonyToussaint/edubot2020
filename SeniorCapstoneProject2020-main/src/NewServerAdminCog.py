"""Module contains cog class for Server Administration Features
"""

# discord imports
import discord
from discord.ext import commands
from discord.ext.commands.errors import CommandInvokeError
from discord import CategoryChannel

# EduBot imports
import EduBotChecks
import EduBotExceptions
import NewBotCache

# other imports
import asyncio
import re
from typing import Union, Optional
from sqlite3 import IntegrityError

class ServerAdministration(commands.Cog, name="Server Administration"):
    """Cog contains methods and listeners for server administration features including
    kick, move, group, role, and poll commands.
    """

    def __init__(self, bot: commands.Bot, cache: NewBotCache.Cache):
        self.bot = bot
        self.cache = cache
        self.managedDeletions = set()

    #### LISTENERS #####################################################################################
    ## Server Initial Configuration ##
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        category_list = guild.categories
        #checks and sees if there are any categories already in the server
        if not category_list:
            category_text = await guild.create_category('Text Channels')
            category_voice = await guild.create_category('Voice Channels')
            await guild.create_text_channel('notifications', \
                                            overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True, connect=False, send_messages=False, view_channel=True)}, \
                                            category=category_text, \
                                            reason=None)
            await guild.create_text_channel('admin-only', \
                                            overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False)}, \
                                            category=category_text, \
                                            reason=None)
            await guild.create_text_channel('student', overwrites=None, category=category_text, reason=None)
            await guild.create_voice_channel('student', overwrites=None, category=category_voice, reason=None)
        #if there are categories, are they text or voice categories, if not create them and create channels under them. If already exist then just create channels
        else:
            for category in category_list:
                if category.name == 'Text Channels':
                    await guild.create_text_channel('notifications', \
                                                    overwrites={guild.deflt_role: discord.PermissionOverwrite(read_messages=True, connect=False, send_messages=False, view_channel=True)}, \
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
        await self.cache.setServerNotificationChannelID(guild.id, commandRestrictionChannel)
        infractionChannel = discord.utils.get(guild.channels, name = "Infraction Channel")
        await self.cache.setServerInfractionChannelID(guild.id, infractionChannel)
        channel_to_send = self.bot.get_channel(commandRestrictionChannel.id)
        message = "The server has been set up with the predefined initial configuration"
        embed = discord.Embed(title="Initial Server Configuration", description=message, color=0x00FF00)
        embed.set_footer(text="Announcement made by EduBot")
        await channel_to_send.send(embed=embed)

        return

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



    #### COMMANDS ###########################################################################################################
    #### Privileged Role Commands ####
    @commands.group(name="privilegedRoles", brief="Parent command for adding and removing privileged roles.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def editAdminRoles(self, ctx):
        """Parent command for adding and removing privileged admin or moderator roles that have permission to
        execute higher level server administration bot commands.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for privilegedRoles command. Use help privilegedRoles for more information.")

    @editAdminRoles.error
    async def editAdminRolesError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @editAdminRoles.command(name="add", brief="Add a role that can execute admin commands.", usage="roleToAdd")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def addPrivilegedRole(self, ctx, roleToAdd: Union[discord.Role, str]):
        """Adds the role specified by roleToAdd to the list of roles that can execute privileged
        commands on this server.
        """
        if(isinstance(roleToAdd, str)):
            if ("*" in roleToAdd):
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
                raise commands.errors.RoleNotFound(roleToAdd)
        else:
            isPrivilegedRole = await self.cache.isPrivilegedRole(ctx.guild.id, roleToAdd.id)
            if (isPrivilegedRole):
                raise EduBotExceptions.RoleAlreadyInCache
        
            await self.cache.addPrivilegedRole(ctx.guild.id, roleToAdd.id)
            await ctx.send(f"{roleToAdd.name} is now a privileged role!")

    @addPrivilegedRole.error
    async def addPrivilegedRoleError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, EduBotExceptions.RoleAlreadyInCache):
            await ctx.send("Error: Role is already a privileged role!")
        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, IntegrityError):
                # if this ever happens I *will* cry, don't test me
                await ctx.send("Error: Failed to cache group roles, please report error to developer!")
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
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, EduBotExceptions.RoleNotInCache):
            await ctx.send("Error: Role isn't a privileged role!")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")



    ## shutdown command ##
    @commands.command(name="shutdown", brief="Shuts down the bot on command")
    @commands.check(EduBotChecks.isEduBotDev)
    async def shutdown_bot(self, ctx):
        await ctx.send("Bye Bye!")
        await ctx.bot.logout()



    #### Channel Commands ####
    @commands.group(name="channel", brief="Parent command for channel commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def channelParent(self, ctx):
        """Parent command for all channel related commands, including creation, deletion,
        and renaming channels.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for channel command. Use help channel for more information.")
    
    @channelParent.error
    async def channelParent_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @channelParent.group(name="create", brief="Parent command for creating new channels.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def channelCreate(self, ctx):
        """Parent command for all channel creation related commands, including text, voice,
        and category creation.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for channel create command. Use help channel create for more information.")

    @channelCreate.error
    async def channelCreate_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @channelCreate.command(name="text", brief="Creates new text channel in server.", usage="newChannelName [categoryName]")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def createTextChannel(self, ctx, channelName: str, categoryName: Optional[str] = None):
        """Creates a new text channel with the given name placed at bottom of channel
        list.
        """
        #category = discord.utils.get(ctx.guild.channels, name = categoryName)
        #category = discord.utils.get(ctx.guild.categories, name = category)
        if (categoryName is not None):
            category = discord.utils.find(lambda category: category.name.lower() == categoryName.lower(), ctx.guild.categories)
            if category is None:
                raise ValueError
            else:
                await ctx.guild.create_text_channel(name=channelName, category = category)
        else:
            await ctx.guild.create_text_channel(name=channelName)

        await ctx.send(f"A new text channel called {channelName} was created.")

    @createTextChannel.error
    async def createTextChannel_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, ValueError):
            await ctx.send("Error: The provided category was not found.")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @channelCreate.command(name="voice", brief="Creates new voice channel in server.", usage="newChannelName")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def createVoiceChannel(self, ctx, channelName: str, categoryName: Optional[str] = None):
        """Creates a new voice channel with the given name placed at bottom of channel
        list.
        """
        if (categoryName is not None):
            category = discord.utils.find(lambda category: category.name.lower() == categoryName.lower(), ctx.guild.categories)
            if category is None:
                raise ValueError
            else:
                await ctx.guild.create_voice_channel(name=channelName, category = category)
        else:
            await ctx.guild.create_voice_channel(name=channelName)

        await ctx.send(f"A new voice channel called {channelName} was created.")

    @createVoiceChannel.error
    async def createVoiceChannel_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, ValueError):
            await ctx.send("Error: The provided category was not found.")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @channelCreate.command(name="category", brief="Creates new category for channels in server.", usage="newCategoryName [role]")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def createCategoryChannel(self, ctx, categoryName: str, role: Optional[discord.Role] = None):
        """Creates a new category with the given name placed at bottom of channel list. 
        If the optional role parameter is provided, will make category private to that role.
        """
        if (role is None):
            overwrites = None
        else:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
                role: discord.PermissionOverwrite(read_messages=True)
            }

        await ctx.guild.create_category(name=categoryName, overwrites=overwrites)
        await ctx.send(f"A new category called {categoryName} was created.")

    @createCategoryChannel.error
    async def createCategoryChannel_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")
    

    @channelParent.command(name="delete", brief="Deletes channels from server.", usage="channelToDelete")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def deleteChannel(self, ctx, channelToDelete: Union[discord.TextChannel, discord.VoiceChannel]):
        """Deletes channel given by channelToDelete from the server.
        """
        await channelToDelete.delete()
        await ctx.send(f"{channelToDelete.name} was deleted.")

    @deleteChannel.error
    async def deleteChannel_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(commands.errors.BadUnionArgument):
            await ctx.send("Error: The supplied channel was not found.")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @channelParent.command(name="rename", brief="Renames the given channel to the new provided name.", usage="channelToRename newName")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def renameChannel(self, ctx, channelToRename: Union[discord.TextChannel, discord.VoiceChannel], newName: str):
        """Renames the channel given by channelToRename to the name given by newName.
        """
        oldName = channelToRename.name
        await channelToRename.edit(name=newName)
        await ctx.send(f"{oldName} was renamed to {newName}.")

    @renameChannel.error
    async def renameChannel_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(commands.errors.BadUnionArgument):
            await ctx.send("Error: The supplied channel was not found.")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")



    #### Role Commands ####
    @commands.group(name="role", brief="Parent command for role commands.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def roleParent(self, ctx):
        """Parent command for all role related commands, including creation, deletion,
         renaming, and assigning members to roles.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for role command. Use help role for more information.")

    @roleParent.error
    async def roleParent_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @roleParent.command(name="create", brief="Creates a new role in server.", usage="newRoleName")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def createRole(self, ctx, newRoleName: str):
        """Creates a new role on the server with default permissions.
        """
        defaultPermission = discord.Permissions(
            view_channel=True,
            change_nickname=True,
            send_messages=True,
            read_messages=True,
            read_message_history=True,
            add_reactions=True,
            attach_files=True,
            connect=True,
            embed_links=True,
            speak=True,
            stream=True,
            use_voice_activation=True
        )
        await ctx.guild.create_role(name=newRoleName, permissions=defaultPermission)
        await ctx.send(f"The role {newRoleName} has been created.")

    @createRole.error
    async def createRole_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @roleParent.command(name="delete", brief="Deletes a role from the server.", usage="roleToDelete")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def deleteRole(self, ctx, roleToDelete: discord.Role):
        """Deletes the role given by roleToDelete from the server.
        """
        roleName = roleToDelete.name
        await roleToDelete.delete()
        await ctx.send(f'The role {roleName} was deleted.')

    @deleteRole.error
    async def deleteRole_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @roleParent.command(name="rename", brief="Renames a role on the server.", usage="roleToRename newName")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def editRoleName(self, ctx, roleToRename: discord.Role, newName: str):
        """Renames the role given by roleToRename to the name given by newName.
        """
        oldName = roleToRename.name
        await roleToRename.edit(name=newName)
        await ctx.send(f'{oldName} was renamed to {newName}')

    @editRoleName.error
    async def editRoleName_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @roleParent.command(name="assign", brief="Assigns given role to the specified member(s).", usage="roleToAssign memberToAssign [memberToAssign...]")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def assignRoles(self, ctx, role: discord.Role, members: commands.Greedy[discord.Member]):
        """Command assigns the supplied role to the supplied space seperated list of server members. 
        Server member can be given by username, username+discriminator#, user mention (@user), or a nickname.
        """
        if (len(members) == 0):
            raise commands.errors.BadArgument

        roleAssignmentCoros = [member.add_roles(role) for member in members]
        await asyncio.wait(roleAssignmentCoros)

        await ctx.send(f"Users have been assigned the {role.name} role.")

    @assignRoles.error
    async def assignRoles_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send(f"Error: members is a required argument that is missing.")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")

    #### Auto-Role Assign Commands ####
    # will generate link that assigns role automatically
    @commands.group(name="link", brief="Parent command for role invite link commands.", case_insensitive=True)
    @commands.check(EduBotChecks.isEduBotDev)
    async def link(self, ctx):
        """Parent command for all role invite link related commands such as link generation, link role assignment,
        link listing and retrieval, and link deletion.
        """
        if (ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for link command. Use help link for more information.")

    @link.error
    async def link_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @link.command(name="generate", brief="generates link", usage="generateLink")
    @commands.check(EduBotChecks.isEduBotDev)
    async def generateLink(self, ctx):
        ''' Will generate link for invite.'''
        generated_link = await ctx.channel.create_invite()
        await ctx.send(f"The generated link:\n{generated_link}")

    @generateLink.error
    async def generateLink_error(self, ctx, error):
        pass


    @link.command(name="assign", brief="assign link to a particular role", usage="roleToAssign [link id...]")
    @commands.check(EduBotChecks.isEduBotDev)
    async def assignLinkRole(self, ctx, role, id):
        ''' Assigns link to have a specific role on join.'''
        get_role_from_name = discord.utils.get(ctx.guild.roles, name=role)
        role_id = get_role_from_name.id
        for invite in await ctx.guild.invites():
            if id == invite.id:
                await self.cache.addRoleInvite(ctx.guild.id, invite.id, role_id)
                #await self.save_links(role, invite)
                await ctx.send(f'the link <{invite}> has been given the role generation of {role}')

    @assignLinkRole.error
    async def assignLinkRole_error(self, ctx, error):
        pass


    @link.command(name="list", brief="returns list of links currently active", usage="listOfLinks")
    @commands.check(EduBotChecks.isEduBotDev)
    async def listLink(self, ctx):
        ''' Shows list of active links.'''
        self.active_links = await ctx.guild.invites()
        if len(self.active_links) != 0:
            await ctx.send(f'**Active Link(s)**: {len(self.active_links)}\n**The Link(s)**:')
            for i in self.active_links:
                await ctx.send(f"<{i}>")
        else:
            await ctx.send("There are no active Link(s).")

    @listLink.error
    async def listLink_error(self, ctx, error):
        pass


    @link.command(name="get", help="returns a specific link you are looking for", usage="getLink [role to feetch ...]")
    @commands.check(EduBotChecks.isEduBotDev)
    async def getLink(self, ctx, role):
        '''get role id from the specified role name in the parameter'''
        get_role_from_name = discord.utils.get(ctx.guild.roles, name=role)
        role_id = get_role_from_name.id
        list_of_links = await self.cache.getServerRoleInvitesList(ctx.guild.id)
        for role_link in list_of_links:
            if int(role_link[1]) == role_id:
                await ctx.send(f'The link for role {role} is:\n  https://discord.gg/{role_link[0]}')

    @getLink.error
    async def getLink(self, ctx, error):
        pass


    @link.command(name="delete", help="delete all invite links", usage="linkToDelete [link id...]")
    @commands.check(EduBotChecks.isEduBotDev)
    async def deleteListLink(self, ctx, id):
        ''' Deletes link.'''
        for invite in await ctx.guild.invites():
            if invite.code == id:
                await self.bot.delete_invite(invite)
                await self.cache.remRoleInvite(ctx.guild.id, invite.code)
                await ctx.send(f'Invite link with ID {id} has been deleted.')
            elif id == "all":
                await self.bot.delete_invite(invite)
                await self.cache.remAllInvite(ctx.guild.id)
                await ctx.send("\nAll active invites have been revoked")

    @deleteListLink.error
    async def deleteListLink_error(self, ctx, error):
        pass


    #### Ban and Unban Commands ####
    @commands.command(name="ban", brief="Bans the user from the server.", usage="userToBan")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def banUser(ctx, userToBan: discord.Member):
        """Ban member given by memberToBan from server. Member can be defined by username,
        username+discriminator, nickname, or mention.
        """
        await userToBan.ban()
        await ctx.send(f'User {userToBan} has been banned')

    @banUser.error
    async def banUser_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")

    @commands.command(name="unban", brief="Unbans the user from the server.", usage="userToUnban")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def unbanUser(ctx, userToUnban: str):
        """Unbans the given user from the server. User must be given by a username+discriminator.
        """
        banned_users = await ctx.guild.bans()
        member_name, member_discriminator = userToUnban.split('#')

        for ban_entry in banned_users:
            user = ban_entry.user

            if(user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                await ctx.send(f'Unbanned {user.mention}')
                return
        
        raise commands.errors.MemberNotFound(userToUnban)

    @unbanUser.error
    async def unbanUser_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send("Error: User specified by userToUnban was not found in the server ban list.")
        elif isinstance(error, ValueError):
            await ctx.send("Error: userToUnban was not formatted correctly. Please use Username+Discriminator format (User#1234).")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")



    #### User Kick Commands ####
    @commands.group(name="kick", brief="Parent command for kick member commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def kick(self, ctx):
        """Parent command for all kick related commands, including kick user, kick role, and kick all.
        """
        if(ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for kick command. Use help kick for more information.")

    @kick.error
    async def kickError(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @kick.command(name="user", brief="Kicks a given user.", usage = "userToKick")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def kickUser(self, ctx, userToKick: Union[discord.Member, str]):
        """Kicks the user provided by userToKick, or if a pattern is provided using * operator, kick all
        users matching that pattern.
        """
        # check to see if wildcard is given
        if(isinstance(userToKick, str)):
            if("*" in userToKick):
                pattern = userToKick
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")
                nameMatch = lambda name: (re.fullmatch(pattern, name.name) is not None) or (re.fullmatch(pattern, str(name.nick)) is not None)
                results = list(filter(nameMatch, ctx.guild.members))

                if (len(results) == 0):
                    raise EduBotExceptions.NoMembersMatchedPattern(userToKick)

                for result in results:
                    await result.kick()
                    await ctx.send("{} has been kicked from the server.".format(result.name))
            else:
                raise commands.errors.MemberNotFound(userToKick)
        else:
            await userToKick.kick()
            await ctx.send("{} has been kicked.".format(userToKick.name))

    @kickUser.error
    async def KickUser_error(self, ctx, error):
        # Runs when there is no user by given name
        if isinstance(error, commands.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An error has occurred: {error}")
        
    
    @kick.command(name="role", help="Kicks all users having a given role.", usage = "roleToKick")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def kickRole(self, ctx, roleToKick: Union[discord.Role, str]):
        """Takes a role group and kicks everyone in that group out of the server. Can also be used with * operator to
        kick members of all roles matching the given pattern.
        """
        if(isinstance(roleToKick, str)):
            if("*" in roleToKick):
                pattern = roleToKick
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")
                
                nameMatch = lambda name: re.fullmatch(pattern, name.name) is not None
                
                results = list(filter(nameMatch, ctx.guild.roles))
                
                if (len(results) == 0):
                    raise EduBotExceptions.NoRolesMatchedPattern(roleToKick)

                for result in results:
                    # Stores list of people to be kicked
                    memberlist = []

                    # Adds people of the given role, and excludes bot
                    for member in ctx.guild.members:
                        if(result in member.roles and (not member.bot)):
                            memberlist.append(member)
                    
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
                raise commands.errors.RoleNotFound(roleToKick)
        else:
            # Stores list of people to be kicked
            memberlist = []

            for member in ctx.guild.members:
                if(roleToKick in member.roles and (not member.bot)):
                    memberlist.append(member)
            
            # Setup for for loop
            Asgrun = []
            for user in memberlist:
                # Kicks every member in list
                Asgrun.extend([user.kick()])
                Asgrun.extend([ctx.send("***{} has been kicked.***".format(user))])
            await asyncio.wait(Asgrun)

    @kickRole.error
    async def kickRole_error(self, ctx, error):
        if isinstance(error, commands.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An error has occurred: {error}")


    @kick.command(name="all", help="Kicks all non-privileged users.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def kickAll(self, ctx):
        """Kicks all non-privileged users from the server. Privileged users are those with a role set using the privilegedRole command.
        """
        # List to store those to kick
        memberlist = []

        # adds members into list, and excludes bot
        for member in ctx.guild.members:
            
            # Seachers for those without Principle role or bot.
            privilegedRoleList = await self.cache.getServerPrivilegedRolesList(ctx.guild.id)
            isPrivileged = any(role.id in privilegedRoleList for role in member.roles)
            if (not isPrivileged and not member.bot):
                memberlist.append(member)
                print(member)
        
        # setup for for loop
        Asgrun = []
        for user in memberlist:
            # kicks all members in list
            Asgrun.extend([user.kick()])
        await asyncio.wait(Asgrun)

        await ctx.send("All members kicked.")

    @kickAll.error
    async def kickAll_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")



    #### User Move Commands ####
    @commands.group(name="move", brief="Parent command for move commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def move(self, ctx):
        """Parent command for all move related commands, including move user, move role, and move channel."""
        if(ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for move command. Use help move for more information.")

    @move.error
    async def move_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occurred: {error}")


    @move.command(name="user", brief="Moves a given user from their current voice channel to another.", usage="userToMove channel")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def moveUser(self, ctx, userToMove: Union[discord.Member, str], channel: discord.VoiceChannel):
        """Will move user from their current voice channel into another, provided they are connected to a voice channel. User 
        given for userToMove can be a username, username+discriminator, nickname, or mention.
        """
        # check to see if wildcard is given
        if(isinstance(userToMove, str)):
            if("*" in userToMove):                
                pattern = userToMove
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")
                nameMatch = lambda name: (re.fullmatch(pattern, name.name) is not None) or (re.fullmatch(pattern, str(name.nick)) is not None)
                results = list(filter(nameMatch, ctx.guild.members))

                if (len(results) == 0):
                    raise EduBotExceptions.NoMembersMatchedPattern(userToMove)

                for result in results:
                    await result.move_to(channel)
            else:
                raise commands.errors.MemberNotFound(userToMove)
        else:
            await userToMove.move_to(channel)
            await ctx.send("Move complete.")
        
    @moveUser.error
    async def moveUser_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, EduBotExceptions.NoMembersMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, CommandInvokeError):
            if isinstance(error.original, discord.HTTPException):
                await ctx.send("Error: Given user is not connected to a voice channel.")
            else:
                await ctx.send(f"An unhandled exception has occured: {error.original}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @move.command(name="role", brief="Moves a given role from a their current voice channel to another.", usage="roleToMove channel")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def moveRole(self, ctx, roleToMove: Union[discord.Role, str], channel: discord.VoiceChannel):
        """Will move all user of role from their current voice channel into another, provided they are connected to a voice channel. Role 
        given for roleToMove can be a role name or mention.
        """
        if(isinstance(roleToMove, str)):
            if("*" in roleToMove):                
                pattern = roleToMove
                for i in ["+", "?", "\\", ".", "^", "[", "]", "$", "&", "|"]:
                    pattern = pattern.replace(i, "\\" + i)
                pattern = pattern.replace("*", ".*")
                nameMatch = lambda name: re.fullmatch(pattern, name.name) is not None
                results = list(filter(nameMatch, ctx.guild.roles))

                if (len(results) == 0):
                    EduBotExceptions.NoRolesMatchedPattern(roleToMove)

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
                raise commands.errors.RoleNotFound(roleToMove)
        else:
            doThisStuff = []
            connectedMembers = []
            for c in ctx.guild.channels:
                if isinstance(c, discord.VoiceChannel):
                    connectedMembers.extend(c.members)
            for user in roleToMove.members:
                if user in connectedMembers:
                    doThisStuff.append(user.move_to(channel))
            await asyncio.wait(doThisStuff)
            await ctx.send("Moves complete.")

    @moveRole.error
    async def moveRole_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, EduBotExceptions.NoRolesMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, ValueError):
            await ctx.send("Error: No members with given role are connected to voice.")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @move.command(name="channel", brief="Moves a given voice channel to another.", usage = "oldChannel newChannel")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def moveChannel(self, ctx, oldChannel: discord.VoiceChannel, newChannel: discord.VoiceChannel):
        """Will move everyone in a channel into a new channel."""
        doThisStuff = []
        for user in oldChannel.members:
            doThisStuff.append(user.move_to(newChannel))
        await asyncio.wait(doThisStuff)
        await ctx.send("Moves complete.")

    @moveChannel.error
    async def moveChannel_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.ChannelNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, ValueError):
            await ctx.send("Error: No members are connected to given voice channel.")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")



    #### Mute Command Group ####
    @commands.group(name="mute", brief="Parent command for mute commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def mute(self, ctx):
        """Mute parent command groups subcommands for applying text chat and voice chat mutes.
        """
        if(ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for mute command. Use help mute for more information.")

    @mute.error
    async def muteUser_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @mute.group(name="user", brief="Parent command for mute user commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def muteUser(self, ctx):
        """Mute user parent command groups subcommands for applying text chat and voice chat mutes
        to individual users.
        """
        if(ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for mute user command. Use help mute user for more information.")

    @muteUser.error
    async def muteUser_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
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
    async def muteUserText_error(self, ctx, error):
        if isinstance(error, EduBotExceptions.NoMembersMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CommandInvokeError):
            if isinstance(error.original, discord.HTTPException):
                await ctx.send("Error: Failed to add mute role to user!")
        elif isinstance(error, discord.Forbidden):
            await ctx.send("Error: You do not have permission to add the mute role!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
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
    async def muteUserVoice_error(self, ctx, error):
        if isinstance(error, EduBotExceptions.NoMembersMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CommandInvokeError):
            if isinstance(error.original, discord.HTTPException):
                await ctx.send("Error: Failed to server mute user, user is not connected to voice channel.")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @mute.group(name="role", brief="Parent command for role mute commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def muteRole(self, ctx):
        """Mute role parent command groups subcommands for applying text chat and voice chat mutes
        to all members of a role.
        """
        if(ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for mute user command. Use help mute user for more information.")

    @muteRole.error
    async def muteRole_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @muteRole.command(name="text", brief="Mutes text chat for given role.", usage="roleToMute")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def muteRoleText(self, ctx, roleToMute: discord.Role):
        """Applies a text chat mute to all members of a given role.
        """
        textMuteRole = discord.utils.get(ctx.guild.roles, name="EduBot_TextMute")
        if (textMuteRole is None):
            textMuteRole = await self.createTextMuteRole(ctx)
        membersToMute = list(filter(lambda member: roleToMute in member.roles, ctx.guild.members))
        roleMuteCoros = [member.add_roles(textMuteRole) for member in membersToMute]
        await asyncio.wait(roleMuteCoros)

        await ctx.send(f'Members with the role {roleToMute.name} have been text muted.')

    @muteRoleText.error
    async def muteRoleText_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, ValueError):
            await ctx.send("Error: There are no members of this role to mute.")
        elif isinstance(error, commands.errors.CommandInvokeError):
            if isinstance(error.original, discord.HTTPException):
                await ctx.send("Error: Failed to add mute role to user!")
        elif isinstance(error, discord.Forbidden):
            await ctx.send("Error: You do not have permission to add the mute role!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @muteRole.command(name="voice", brief="Mutes voice chat for given role.", usage="roleToMute")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def muteRoleVoice(self, ctx, roleToMute: discord.Role):
        """Applies a voice chat mute to all members of a given role.
        """
        membersToMute = list(filter(lambda member: (roleToMute in member.roles) and (member.voice.channel is not None), ctx.guild.members))
        roleMuteCoros = [member.edit(mute=True) for member in membersToMute]
        await asyncio.wait(roleMuteCoros)

        await ctx.send(f'Members with the role {roleToMute.name} have been voice muted.')

    @muteRoleVoice.error
    async def muteRoleVoice_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, ValueError):
            await ctx.send("Error: There are no members of this role to mute.")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CommandInvokeError):
            if isinstance(error.original, discord.HTTPException):
                await ctx.send("Error: Failed to add server mute to user, user is not connected to voice channel.")
            elif isinstance(error, AttributeError):
                await ctx.send("Error: There are no members of this role connected to voice.")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")



    #### Unmute Command Group ####
    @commands.group(name="unmute", brief="Parent command for unmute commands.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def unmute(self, ctx):
        """Unmute parent command groups subcommands for removing text chat and voice chat mutes.
        """
        if(ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for unmute command. Use help unmute for more information.")

    @unmute.error
    async def unmute_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @unmute.group(name="user", brief="Parent command for unmute user commands.", case_insensitive=True)
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def unmuteUser(self, ctx):
        """Unmute user parent command groups subcommands for removing text chat and voice chat mutes from
        individual users.
        """
        if(ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for unmute user command. Use help unmute user for more information.")

    @unmuteUser.error
    async def unmuteUser_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
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
    async def unmuteUserText_error(self, ctx, error):
        if isinstance(error, EduBotExceptions.NoMembersMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, discord.HTTPException):
            await ctx.send("Error: Failed to remove mute role from role members!")
        elif isinstance(error, discord.Forbidden):
            await ctx.send("Error: You do not have permission to remove the mute role!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
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
    async def unmuteUserVoice_error(self, ctx, error):
        if isinstance(error, EduBotExceptions.NoMembersMatchedPattern):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.MemberNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, discord.HTTPException):
            await ctx.send("Error: Failed to remove mute role from user!")
        elif isinstance(error, discord.Forbidden):
            await ctx.send("Error: You do not have permission to remove the mute role!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")

  
    @unmute.group(name="role", brief="Parent command for unmute role commands.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def unmuteRole(self, ctx):
        """Unmute parent command groups subcommands for removing text chat and voice chat mutes for all
        members of a given role.
        """
        if(ctx.invoked_subcommand is None):
            await ctx.send("No subcommand provided for unmute role command. Use help unmute role for more information.")
        
    @unmuteRole.error
    async def unmuteRole_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")

    
    @unmuteRole.command(name="text", brief="Unmutes text chat for members of role.", usage="roleToUnmute")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def unmuteRoleText(self, ctx, roleToUnmute: discord.Role):
        """Removes text chat mute from all members of a given role.
        """
        textMuteRole = discord.utils.get(ctx.guild.roles, name="EduBot_TextMute")
        if (textMuteRole is None):
            textMuteRole = await self.createTextMuteRole(ctx)
        membersToMute = list(filter(lambda member: roleToUnmute in member.roles, ctx.guild.members))
        roleMuteCoros = [member.remove_roles(textMuteRole) for member in membersToMute]
        await asyncio.wait(roleMuteCoros)

        await ctx.send(f'Members with the role {roleToUnmute.name} have been unmuted.')

    @unmuteRoleText.error
    async def unmuteRoleText_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, ValueError):
            await ctx.send("Error: There are no members of this role to unmute.")
        elif isinstance(error, discord.HTTPException):
            await ctx.send("Error: Failed to remove mute role from user!")
        elif isinstance(error, discord.Forbidden):
            await ctx.send("Error: You do not have permission to remove the mute role!")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")


    @unmuteRole.command(name="voice", brief="Unmutes voice chat for members of role.", usage="roleToUnmute")
    async def unmuteRoleVoice(self, ctx, roleToUnmute: discord.Role):
        """Removes a voice chat mute from all members of a given role.
        """
        membersToMute = list(filter(lambda member: (roleToUnmute in member.roles) and (member.voice.channel is not None), ctx.guild.members))
        roleMuteCoros = [member.edit(mute=False) for member in membersToMute]
        await asyncio.wait(roleMuteCoros)

        await ctx.send(f'Members with the role {roleToUnmute.name} have been unmuted.')

    @unmuteRoleVoice.error
    async def unmuteRoleVoice_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, ValueError):
            await ctx.send("Error: There are no members of this role to mute.")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.errors.CommandInvokeError):
            if isinstance(error.original, discord.HTTPException):
                await ctx.send("Error: Failed to remove server mute from user, user is not connected to voice channel.")
            elif isinstance(error, AttributeError):
                await ctx.send("Error: There are no members of this role connected to voice.")
        else:
            await ctx.send(f"An unhandled exception has occured: {error}")



    #### HELPER METHODS #####################################################################################################
    async def createTextMuteRole(self, ctx) -> discord.Role:
        """Creates a text mute role on the current server and configures the permissions overwrites of
        each channel on the server to disallow the text mute role from sending messages on the channel.
        """
        muteRole = await ctx.guild.create_role(name="EduBot_TextMute")
        permissionConfigCoros = []
        for channel in ctx.guild.channels:
            if (isinstance(channel, discord.CategoryChannel) or isinstance(channel, discord.TextChannel)):
                if (not channel.permissions_synced):
                    permissionConfigCoros.append(channel.set_permissions(target=muteRole, send_messages=False))
        
        await asyncio.wait(permissionConfigCoros)
        return muteRole
