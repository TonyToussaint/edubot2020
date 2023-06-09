import pytest
import NewBotCache
import discord

@pytest.fixture
def emptyCache():
    cache = NewBotCache.Cache(':memory:')

    # insert server
    insertStatement = """INSERT INTO servers(id, command_prefix, is_locked) VALUES(?,?,?)"""
    cache.dbConnection.execute(insertStatement, ("798358551230677042",'!',False))

    return cache

@pytest.fixture
def sampleCache():
    cache = NewBotCache.Cache(':memory:')
    # insert server
    insertStatement = """INSERT INTO servers(id, command_prefix, is_locked) VALUES(?,?,?)"""
    parameters = [
        ("798358551230677042",'!',False),
        ("820724374268149771",'!',False)
    ]
    cache.dbConnection.executemany(insertStatement, parameters)

    # insert roles
    insertStatement = """INSERT INTO perm_overwrites(channel_id, modified_id, server_id, allow_value, deny_value) VALUES(?,?,?,?,?)"""
    parameters = [
        ("808765968746283048", "798359230183636994", "798358551230677042", "871890001", "0"),
        ("808765968746283048", "805602260993310752", "798358551230677042", "0", "2048"),
        ("808765968746283047", "805602260993310752", "820724374268149771", "0", "2048")
    ]
    cache.dbConnection.executemany(insertStatement, parameters)

    return cache

@pytest.fixture
def sampleOverwrite():
    allow = discord.Permissions.none()
    deny = discord.Permissions(send_messages=True)
    overwrite = discord.PermissionOverwrite.from_pair(allow, deny)
    return overwrite

## unit tests ##
@pytest.mark.asyncio
async def testAddPermOverwrite_CorrectInput(emptyCache: NewBotCache.Cache, sampleOverwrite: discord.PermissionOverwrite): # !!! #
    await emptyCache.addPermOverwrite(798358551230677042, 808765968746283048, 798359404821872661, sampleOverwrite)
    
    cursor = emptyCache.createCursor()
    selectStatement = """SELECT allow_value, deny_value FROM perm_overwrites 
    WHERE server_id = '798358551230677042' AND channel_id = '808765968746283048' AND modified_id = '798359404821872661'"""

    cursor.execute(selectStatement)
    allow_value, deny_value = cursor.fetchone()
    allow = discord.Permissions(permissions=int(allow_value))
    deny = discord.Permissions(permissions=int(deny_value))
    overwrite = discord.PermissionOverwrite.from_pair(allow, deny)

    assert overwrite == sampleOverwrite

@pytest.mark.asyncio
async def testAddPermOverwrite_DuplicatePK(sampleCache: NewBotCache.Cache, sampleOverwrite: discord.PermissionOverwrite): # !!! #
    await sampleCache.addPermOverwrite(798358551230677042, 808765968746283048, 798359230183636994, sampleOverwrite)

    cursor = sampleCache.createCursor()
    selectStatement = """SELECT allow_value, deny_value FROM perm_overwrites 
    WHERE server_id = '798358551230677042' AND channel_id = '808765968746283048' AND modified_id = '798359230183636994'"""

    cursor.execute(selectStatement)
    allow_value, deny_value = cursor.fetchone()
    allow = discord.Permissions(permissions=int(allow_value))
    deny = discord.Permissions(permissions=int(deny_value))
    overwrite = discord.PermissionOverwrite.from_pair(allow, deny)

    assert overwrite == sampleOverwrite

@pytest.mark.asyncio
async def testAddPermOverwrite_None(emptyCache: NewBotCache.Cache, sampleOverwrite: discord.PermissionOverwrite):
    pass

##########################################################################################################

@pytest.mark.asyncio
async def testRemPermOverwrite_Guild(sampleCache: NewBotCache.Cache): # !!! #
    await sampleCache.remPermOverwrite(798358551230677042)

    cursor = sampleCache.createCursor()
    selectStatement = """SELECT * FROM perm_overwrites"""

    expectedResult = [
        ("808765968746283047", "805602260993310752", "820724374268149771", "0", "2048")
    ]

    cursor.execute(selectStatement)
    result = cursor.fetchall()
    assert result == expectedResult

@pytest.mark.asyncio
async def testRemPermOverwrite_NonIntGuild(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testRemPermOverwrite_NoneGuild(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testRemPermOverwrite_Channel(sampleCache: NewBotCache.Cache): # !!! #
    await sampleCache.remPermOverwrite(798358551230677042, 808765968746283048)

    cursor = sampleCache.createCursor()
    selectStatement = """SELECT * FROM perm_overwrites"""

    expectedResult = [
        ("808765968746283047", "805602260993310752", "820724374268149771", "0", "2048")
    ]

    cursor.execute(selectStatement)
    result = cursor.fetchall()
    assert result == expectedResult

@pytest.mark.asyncio
async def testRemPermOverwrite_NonIntChannel(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testRemPermOverwrite_RoleUser(sampleCache: NewBotCache.Cache): # !!! #
    await sampleCache.remPermOverwrite(798358551230677042, 808765968746283048, 798359230183636994)

    cursor = sampleCache.createCursor()
    selectStatement = """SELECT * FROM perm_overwrites"""

    expectedResult = [
        ("808765968746283048", "805602260993310752", "798358551230677042", "0", "2048"),
        ("808765968746283047", "805602260993310752", "820724374268149771", "0", "2048")
    ]

    cursor.execute(selectStatement)
    result = cursor.fetchall()
    assert result == expectedResult

@pytest.mark.asyncio
async def testRemPermOverwrite_NonIntRoleUser(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testRemPermOverwrite_NoneChannelNotNoneRole(sampleCache: NewBotCache.Cache):
    pass

##########################################################################################################

@pytest.mark.asyncio
async def testGetPermOverwrite_CorrectInput(sampleCache: NewBotCache.Cache): # !!! #
    allow = discord.Permissions(0)
    deny = discord.Permissions(2048)
    expectedResult = discord.PermissionOverwrite.from_pair(allow, deny)

    result = await sampleCache.getPermOverwrite(820724374268149771, 808765968746283047, 805602260993310752)

    assert result == expectedResult

@pytest.mark.asyncio
async def testGetPermOverwrite_NonExistantGuild(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testGetPermOverwrite_NonExistantChannel(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testGetPermOverwrite_NonExistantRoleUser(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testGetPermOverwrite_NonIntGuild(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testGetPermOverwrite_NonIntChannel(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testGetPermOverwrite_NonIntUserRole(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testGetPermOverwrite_NoneGuild(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testGetPermOverwrite_NoneChannel(sampleCache: NewBotCache.Cache):
    pass

@pytest.mark.asyncio
async def testGetPermOverwrite_NoneRoleUser(sampleCache: NewBotCache.Cache):
    pass

##########################################################################################################

@pytest.mark.asyncio
async def testGetChannelOverwriteList_CorrectInput(sampleCache: NewBotCache.Cache): # !!! #
    results = await sampleCache.getChannelOverwritesList(798358551230677042, 808765968746283048)
    
    expectedResults = [
        (798359230183636994, discord.PermissionOverwrite.from_pair(discord.Permissions(871890001), discord.Permissions(0))),
        (805602260993310752, discord.PermissionOverwrite.from_pair(discord.Permissions(0), discord.Permissions(2048)))
    ]

    compareTuples = lambda tupleOne, tupleTwo: (tupleOne[0] == tupleTwo[0]) and (tupleOne[1] == tupleTwo[1])
    
    assert all([compareTuples(result, expectedResult) for result, expectedResult in zip(results, expectedResults)])

@pytest.mark.asyncio
async def testGetChannelOverwriteList_NonExistant(sampleCache: NewBotCache.Cache):
    pass

##########################################################################################################

@pytest.mark.asyncio
async def testUpdateOverwriteChannel_CorrectInput(sampleCache: NewBotCache.Cache): # !!! #
    await sampleCache.updateOverwriteChannel(798358551230677042, 808765968746283048, 808765968746286969)

    expectedResult = [
        ("808765968746286969", "798359230183636994", "798358551230677042", "871890001", "0"),
        ("808765968746286969", "805602260993310752", "798358551230677042", "0", "2048"),
        ("808765968746283047", "805602260993310752", "820724374268149771", "0", "2048")
    ]

    selectStatement = """SELECT * FROM perm_overwrites"""
    cursor = sampleCache.createCursor()
    cursor.execute(selectStatement)
    result = cursor.fetchall()
    assert result == expectedResult

@pytest.mark.asyncio
async def testUpdateOverwriteChannel_NonExistant(sampleCache: NewBotCache.Cache):
    pass