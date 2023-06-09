"""Module contains custom written checks for EduBot."""

# boolean stores whether the current iteration of the bot is a dev-build
DEV_BUILD = True

# stores reference to cache object to allow checks to use cache
cache = None

def setCacheReference(cacheRef):
    global cache
    cache = cacheRef

# check will see if the user who issued a bot command is a server owner
# or a role specified as a moderator or bot operator to the bot by the server owner
async def hasElevatedPrivileges(ctx):
    isDev = await isEduBotDev(ctx)
    isOwner = ctx.author.id == ctx.guild.owner_id
    privilegedRoleList = await cache.getServerPrivilegedRolesList(ctx.guild.id)
    isPrivileged = any(role.id in privilegedRoleList for role in ctx.author.roles)
    # try:
    #     # isPrivileged = any(role.id in cache.privilegedRolesCache[str(ctx.guild.id)] for role in ctx.author.roles)
    #     # isPrivileged = any(role.name == "Principle" for role in ctx.author.roles)
    # except KeyError:
    #     isPrivileged = False

    return any([isDev, isOwner, isPrivileged])

# check will see if the user who issed a bot command is a EduBot developer; this check should be removed in
# official builds to prevent developers from being able to access adminstrative commands
async def isEduBotDev(ctx):
    if (DEV_BUILD):
        return ctx.author.id in {
            210687957768601600,
            269684001424408577,
            428548599505223681,
            250433861320704001,
            373992852323303427,
            324018912507199489,
            166331247482634240
            }
    else:
        return False