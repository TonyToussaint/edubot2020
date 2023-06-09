#allows the trusted member to allow roles from the bot
@client.command(name="allowrole")
@client.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member = None, *, role: discord.Role = None):
        if role == None:
                await ctx.send(f'Provide a role to add')
                return

        if member == None:
                await ctx.send(f'Provide a member edit to add a role')
                return

        await member.add_roles(role)
        await ctx.send(f"Successfully added role, {role} to {member.name}")
