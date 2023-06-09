import sqlite3
import discord
from discord.ext.commands.errors import BadArgument
import pytest
import NewBotCache

## fixtures ##
@pytest.fixture
def sampleCache():
    cache = NewBotCache.Cache(':memory:')

    insertStatement = """INSERT INTO servers(id, command_prefix, is_locked, infraction_channel, notification_channel) VALUES(?,?,?,?,?)"""
    parameters = [
        ("798358551230677042",'!',0,None,None),
        ("394215266986491904",'.',1,"394215266986491906","739359547025522740")
    ]
    cache.dbConnection.executemany(insertStatement, parameters)


    return cache


## unit tests ##
@pytest.mark.asyncio
async def testAddServer_CorrectInput():
    cache = NewBotCache.Cache(':memory:')
    await cache.addServer(798358551230677042)

    expectedResult = [
        ("798358551230677042", "!", None, None, 0)
    ]
    cursor = cache.createCursor()
    selectStatement = """SELECT * FROM servers"""
    cursor.execute(selectStatement)
    result = cursor.fetchall()

    assert result == expectedResult

@pytest.mark.asyncio
async def testAddServer_NonInt():
    cache = NewBotCache.Cache(':memory:')
    with pytest.raises(TypeError):
        await cache.addServer("test")

@pytest.mark.asyncio
async def testAddServer_None():
    cache = NewBotCache.Cache(':memory:')
    with pytest.raises(sqlite3.IntegrityError):
        await cache.addServer(None)

##########################################################################################################

@pytest.mark.asyncio
async def testRemServer_CorrectInput(sampleCache: NewBotCache.Cache):
    await sampleCache.remServer(798358551230677042)

    expectedResult = [
        ("394215266986491904",'.',"394215266986491906","739359547025522740",1)
    ]
    cursor = sampleCache.createCursor()
    selectStatement = """SELECT * FROM servers"""
    cursor.execute(selectStatement)
    result = cursor.fetchall()

    assert result == expectedResult

@pytest.mark.asyncio
async def testRemServer_NonInt(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.remServer("test")

@pytest.mark.asyncio
async def testRemServer_NonExistant(sampleCache: NewBotCache.Cache):
    await sampleCache.remServer(798358551230677041)

    expectedResult = ("798358551230677042", "!", None, None, 0)
    cursor = sampleCache.createCursor()
    selectStatement = """SELECT * FROM servers"""
    cursor.execute(selectStatement)
    result = cursor.fetchone()

    assert result == expectedResult

@pytest.mark.asyncio
async def testRemServer_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.remServer(None)

##########################################################################################################

@pytest.mark.asyncio
async def testGetServerCommandPrefix_CorrectInput(sampleCache: NewBotCache.Cache):
    result_one = await sampleCache.getServerCommandPrefix(798358551230677042)
    result_two = await sampleCache.getServerCommandPrefix(394215266986491904)
    assert (result_one == "!") and (result_two == ".")

@pytest.mark.asyncio
async def testGetServerCommandPrefix_NonExistant(sampleCache: NewBotCache.Cache):
    expectedResult = '!'
    result = await sampleCache.getServerCommandPrefix(798358551230677041)
    assert result == expectedResult

@pytest.mark.asyncio
async def testGetServerCommandPrefix_NonInt(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.getServerCommandPrefix("value")

@pytest.mark.asyncio
async def testGetServerCommandPrefix_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.getServerCommandPrefix(None)

##########################################################################################################

@pytest.mark.asyncio
async def testSetServerCommandPrefix_CorrectInput(sampleCache: NewBotCache.Cache):
    await sampleCache.setServerCommandPrefix(798358551230677042, ".")
    
    expectedResult = "."
    result = await sampleCache.getServerCommandPrefix(798358551230677042)

    assert result == expectedResult

@pytest.mark.asyncio
async def testSetServerCommandPrefix_EmptyString(sampleCache: NewBotCache.Cache):
    with pytest.raises(BadArgument):
        await sampleCache.setServerCommandPrefix(798358551230677042, "")

@pytest.mark.asyncio
async def testSetServerCommandPrefix_TooLongString(sampleCache: NewBotCache.Cache):
    with pytest.raises(BadArgument):
        await sampleCache.setServerCommandPrefix(798358551230677042, "!!")

@pytest.mark.asyncio
async def testSetServerCommandPrefix_NonString(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerCommandPrefix(798358551230677042, 1)

@pytest.mark.asyncio
async def testSetServerCommandPrefix_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(sqlite3.IntegrityError):
        await sampleCache.setServerCommandPrefix(798358551230677042, None)

##########################################################################################################

@pytest.mark.asyncio
async def testGetServerLockStatus_CorrectInput(sampleCache: NewBotCache.Cache):
    result_one = await sampleCache.getServerLockStatus(798358551230677042)
    result_two = await sampleCache.getServerLockStatus(394215266986491904)
    assert (not result_one) and result_two

@pytest.mark.asyncio
async def testGetServerLockStatus_NonExistant(sampleCache: NewBotCache.Cache):
    expectedResult = None
    result = await sampleCache.getServerLockStatus(798358551230677041)
    assert result == expectedResult

@pytest.mark.asyncio
async def testGetServerLockStatus_NonInt(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.getServerLockStatus("test")

@pytest.mark.asyncio
async def testGetServerLockStatus_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.getServerLockStatus(None)

##########################################################################################################

@pytest.mark.asyncio
async def testSetServerLockStatus_CorrectInput(sampleCache: NewBotCache.Cache):
    await sampleCache.setServerLockStatus(798358551230677042, True)
    
    expectedResult = True
    result = await sampleCache.getServerLockStatus(798358551230677042)

    assert result == expectedResult

@pytest.mark.asyncio
async def testSetServerLockStatus_NonExistant(sampleCache: NewBotCache.Cache):
    cursor = sampleCache.createCursor()
    selectStatement = """SELECT is_locked FROM servers"""
    cursor.execute(selectStatement)
    before = cursor.fetchall()

    await sampleCache.setServerLockStatus(798358551230677041, True)
    cursor.execute(selectStatement)
    after = cursor.fetchall()

    assert before == after

@pytest.mark.asyncio
async def testSetServerLockStatus_NonInt(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerLockStatus("test", True)

@pytest.mark.asyncio
async def testSetServerLockStatus_NonBool(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerLockStatus(798358551230677042, 1)

@pytest.mark.asyncio
async def testSetServerLockStatus_NoneServerID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerLockStatus(None, True)

@pytest.mark.asyncio
async def testSetServerLockStatus_NoneLockStatus(sampleCache: NewBotCache.Cache):
    with pytest.raises(sqlite3.IntegrityError):
        await sampleCache.setServerLockStatus(798358551230677042, None)

##########################################################################################################

@pytest.mark.asyncio
async def testGetServerInfractionChannelID_CorrectInput(sampleCache: NewBotCache.Cache):
    result_one = await sampleCache.getServerInfractionChannelID(798358551230677042)
    result_two = await sampleCache.getServerInfractionChannelID(394215266986491904)
    assert (result_one is None) and (result_two == 394215266986491906)

@pytest.mark.asyncio
async def testGetServerInfractionChannelID_NonExistant(sampleCache: NewBotCache.Cache):
    expectedResult = None
    result = await sampleCache.getServerInfractionChannelID(798358551230677041)
    assert result == expectedResult

@pytest.mark.asyncio
async def testGetServerInfractionChanneID_NonInt(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.getServerInfractionChannelID("test")

@pytest.mark.asyncio
async def testGetServerInfractionChannelID_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.getServerInfractionChannelID(None)

##########################################################################################################

@pytest.mark.asyncio
async def testSetServerInfractionChannelID_CorrectInput(sampleCache: NewBotCache.Cache):
    await sampleCache.setServerInfractionChannelID(798358551230677042, 820399043238035456)
    
    expectedResult = 820399043238035456
    result = await sampleCache.getServerInfractionChannelID(798358551230677042)

    assert result == expectedResult

@pytest.mark.asyncio
async def testSetServerInfractionChannelID_NonExistant(sampleCache: NewBotCache.Cache):
    cursor = sampleCache.createCursor()
    selectStatement = """SELECT infraction_channel FROM servers"""
    cursor.execute(selectStatement)
    before = cursor.fetchall()

    await sampleCache.setServerInfractionChannelID(798358551230677041, 820399043238035456)
    cursor.execute(selectStatement)
    after = cursor.fetchall()

    assert before == after

@pytest.mark.asyncio
async def testSetServerInfractionChannelID_NonIntServerID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerInfractionChannelID("test", 820399043238035456)

@pytest.mark.asyncio
async def testSetServerInfractionChannelID_NonIntChannelID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerInfractionChannelID(798358551230677042, "test")

@pytest.mark.asyncio
async def testSetServerInfractionChannelID_NoneServerID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerInfractionChannelID(None, 820399043238035456)

@pytest.mark.asyncio
async def testSetServerInfractionChannelID_NoneChannelID(sampleCache: NewBotCache.Cache):
    expectedResult = None
    await sampleCache.setServerInfractionChannelID(798358551230677042, None)
    result = await sampleCache.getServerInfractionChannelID(798358551230677042)
    assert result == expectedResult

##########################################################################################################

@pytest.mark.asyncio
async def testGetServerNotificationChannelID_CorrectInput(sampleCache: NewBotCache.Cache):
    result_one = await sampleCache.getServerNotificationChannelID(798358551230677042)
    result_two = await sampleCache.getServerNotificationChannelID(394215266986491904)
    assert (result_one is None) and (result_two == 739359547025522740)

@pytest.mark.asyncio
async def testGetServerNotificationChannelID_NonExistant(sampleCache: NewBotCache.Cache):
    expectedResult = None
    result = await sampleCache.getServerNotificationChannelID(798358551230677041)
    assert result == expectedResult

@pytest.mark.asyncio
async def testGetServerNotificationChannelID_NonInt(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.getServerNotificationChannelID("test")

@pytest.mark.asyncio
async def testGetServerNotificationChannelID_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.getServerNotificationChannelID(None)

##########################################################################################################

@pytest.mark.asyncio
async def testSetServerNotificationChannelID(sampleCache: NewBotCache.Cache):
    await sampleCache.setServerNotificationChannelID(798358551230677042, 808765968746283048)
    
    expectedResult = 808765968746283048
    result = await sampleCache.getServerNotificationChannelID(798358551230677042)

    assert result == expectedResult

@pytest.mark.asyncio
async def testSetServerNotificationChannelID_NonExistant(sampleCache: NewBotCache.Cache):
    cursor = sampleCache.createCursor()
    selectStatement = """SELECT notification_channel FROM servers"""
    cursor.execute(selectStatement)
    before = cursor.fetchall()

    await sampleCache.setServerNotificationChannelID(798358551230677041, 820399043238035456)
    cursor.execute(selectStatement)
    after = cursor.fetchall()

    assert before == after

@pytest.mark.asyncio
async def testSetServerNotificationChannelID_NonIntServerID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerNotificationChannelID("test", 820399043238035456)

@pytest.mark.asyncio
async def testSetServerNotificationChannelID_NonIntChannelID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerNotificationChannelID(798358551230677042, "test")

@pytest.mark.asyncio
async def testSetServerNotificationChannelID_NoneServerID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.setServerNotificationChannelID(None, 820399043238035456)

@pytest.mark.asyncio
async def testSetServerNotificationChannelID_NoneChannelID(sampleCache: NewBotCache.Cache):
    expectedResult = None
    await sampleCache.setServerNotificationChannelID(798358551230677042, None)
    result = await sampleCache.getServerNotificationChannelID(798358551230677042)
    assert result == expectedResult

