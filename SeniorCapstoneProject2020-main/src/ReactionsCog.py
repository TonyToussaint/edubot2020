import asyncio
import BotCache
import EduBotChecks
import EduBotExceptions
import discord
from discord.ext import commands

#Global message var to be used for initial reaction message
msg = None

class Reactions(commands.Cog, name="Reactions"):
	"""
    Cog contains methods & listeners for reactions on messages to gain or remove roles 
    """
	def __init__(self, bot):
		self.bot = bot 

	#Sets the initial message to react to when the bot starts up
	@commands.Cog.listener()
	async def on_ready(self):
		#channel = self.bot.get_channel(789250695756513332) #Tone's server - Welcome channel
		channel = self.bot.get_channel(804175141243322428) #Caplet University - General channel
		global msg
		msg = await channel.send(f"React to this to get the Test role! Remove reaction to remove role!")
		#await self.bot.add_reaction(msg, ) #Was testing this out with specific emojis, no luck yet
	
	#Listens & gives Role to user who has reacted to the message
	#This method currently only works for messages that are in the cache, older messages will not work - trying raw reaction method for more permanent ideas
	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, user):
		if reaction.message == msg:
			channel = self.bot.get_channel(804175141243322428) #Caplet University - General channel
			role = discord.utils.get(user.guild.roles, name = 'Test')
			await user.add_roles(role)
			
			#Prints to console
			print(f"{user.display_name} reacted with {reaction.emoji}")
			#Outputs to channel
			await channel.send(f"{user.display_name} has been granted the Test role")
	
	#Removes role from user once that user has removed their reaction 
	#This method currently only works for messages that are in the cache, older messages will not work - trying raw reaction method for more permanent ideas
	@commands.Cog.listener()
	async def on_reaction_remove(self, reaction, user):
		if reaction.message == msg:
			channel = self.bot.get_channel(804175141243322428) #Caplet University - General channel
			role = discord.utils.get(user.guild.roles, name = 'Test')
			await user.remove_roles(role)

			#Prints to console
			print(f"{user.display_name} removed their reaction {reaction.emoji}")
			#Outputs to channel
			await channel.send(f"{user.display_name} no longer has the Test role")

	#Not firing for some reason, this would be a more permanent way to add reactions to get roles even if the message is really old
	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload):
		channel = self.bot.get_channel(789250695756513332)
		global msg
		if payload.message_id == '821564801162805259':
			role = discord.utils.get(payload.member.guild.roles, name = 'tester')
			await payload.member.add_roles(role)
			#Prints to console 
			print(f"[RAW] {payload.member.display_name} reacted with {payload.emoji}")

	#Still needs work, raw remove function doesnt work the same as raw add
#	@commands.Cog.listener()
#	async def on_raw_reaction_remove(self, payload):
#		member = self.bot.get_member(payload.user_id)
#		print(f"[RAW] {member.display_name} removed their reaction of {payload.emoji}")
