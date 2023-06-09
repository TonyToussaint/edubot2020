"""Module contains cog class for Notification System Features"""

import asyncio
from random import shuffle
from typing import Union, Optional
import NewBotCache
import EduBotChecks
import EduBotExceptions
import ServerAdminCog
import discord
from discord.ext import commands, timers, tasks
from discord.ext.commands.errors import BadArgument, RoleNotFound, UserNotFound
from datetime import datetime, timedelta, date

class NotificationSystem(commands.Cog, name="Notification System"):
    """
    Cog contains methods and listeners for notification system features including
    automated announcements and assignment tracking
    """
    
    def __init__(self, bot: commands.Bot, cache: NewBotCache.Cache):
        self.bot = bot
        self.cache = cache

    #### COMMANDS ####


    @commands.command(name="announce", help="Creates an announcement in the \"notifications\" channel with a given message.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def announce(self, ctx, *, message):
        #gets the channel named "notification"
        channel = await self.cache.getServerNotificationChannelID(message.guild.id)
        commandRestrictionChannel = self.bot.get_channel(channel)
        #commandRestrictionChannel = discord.utils.get(ctx.guild.channels, name='notifications')
        #checks to see if the channel that the command is invoked from is the allowed channel
        if ctx.channel.id == commandRestrictionChannel.id:
            #delete the invoked command
            await ctx.message.delete()
            #creates the announcements
            embed = discord.Embed(title="Announcement", description=message, color=0x00FF00)
            embed.set_footer(text="Announcement made by {}".format(ctx.message.author.name))
            await ctx.channel.send(embed=embed)
        #error handling in case command is invoked from restricted channel
        else:
            await ctx.message.delete()
            await ctx.send("This command is only allowed in the notifications channel!")

    #Timed Reminder, not finished this is just the design to understand how it works
    @commands.command(name="remind", help="Creates a reminder with a given message to be displayed at a given time.")
    @commands.check(EduBotChecks.hasElevatedPrivileges)
    async def remind(self, ctx, message, time , reminder_time: int):
        channel = await self.cache.getServerNotificationChannelID(message.guild.id)
        commandRestrictionChannel = self.bot.get_channel(channel)
        #commandRestrictionChannel = discord.utils.get(ctx.guild.channels, name='notifications')
        if ctx.channel.id == commandRestrictionChannel.id:
            await ctx.message.delete()
            while True:
                time_format = "%Y-%m-%d %H:%M:%S"
                time_now = datetime.now(tz=None)
                input_time = datetime.strptime(time, time_format)
                #finding time difference
                time_difference = input_time - time_now
                #calculating days and hours and minutes difference
                day_left = time_difference.days
                hour_left = int(time_difference.total_seconds()/3600)
                minute_left = int(time_difference.total_seconds()/60)
                #to send reminder at the beginning of every minute
                exact_minute = int(time_now.second)
                if time_now.strftime('%Y') > input_time.strftime('%Y'):
                    await ctx.send ("The year you have entered is invalid, the year {} has already passed. The current year is {}".format(input_time.strftime('%Y'), time_now.strftime('%Y')))
                    return False

                elif time_now.strftime('%Y') <= input_time.strftime('%Y') and time_now.strftime('%m') > input_time.strftime('%m'):
                    await ctx.send ("The month you have entered is invalid, the month {} has already passed. The current month is {}".format(input_time.strftime('%m'), time_now.strftime('%m')))
                    return False

                elif time_now.strftime('%d') == input_time.strftime('%d') and time_now.strftime('%H') > input_time.strftime('%H'):
                    await ctx.send ("The time you entered is invalid, the time {} has already passed. The current time is {}".format(input_time.strftime('%H:%M:%S'), time_now.strftime('%H:%M:%S')))
                    return False
                else:
                    #setting up the format for how to display the reminder
                    if minute_left != 0:
                        message_to_send = ("**Remaining Time:**\n\nDays left: {}\nHours Left: {}\nMinutes left: {}".format(day_left,hour_left,minute_left))
                        embed_reminder = discord.Embed(title="REMINDER: {}".format(message), description=message_to_send, color=0xFF0000)
                        embed_reminder.set_footer(text="Reminder set by {}".format(ctx.message.author.name))
                        await ctx.send(embed=embed_reminder)
                    else:
                        message_to_send = ("The time is up!")
                        embed_reminder = discord.Embed(title="REMINDER: {}".format(message), description=message_to_send, color=0xFF0000)
                        embed_reminder.set_footer(text="Reminder set by {}".format(ctx.message.author.name))
                        await ctx.send(embed=embed_reminder)
                        return False

                await asyncio.sleep(reminder_time-exact_minute)

        else:
            await ctx.send("This command is only allowed in the notifications channel!")