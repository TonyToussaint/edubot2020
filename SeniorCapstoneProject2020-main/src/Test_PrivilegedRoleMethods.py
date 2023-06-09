import pytest
import NewBotCache
from sqlite3.dbapi2 import IntegrityError


from collections import Counter

# lambda function for testing equality between unordered lists
compare = lambda x, y: Counter(x) == Counter(y)

@pytest.fixture
def emptyCache():
    cache = NewBotCache.Cache(':memory:')

    # insert server
    insertStatement = """INSERT INTO servers(id, command_prefix, is_locked) VALUES(?,?,?)"""
    cache.createCursor().execute(insertStatement, (798358551230677042, '!', False))

    return cache

@pytest.fixture
def sampleCache():
    cache = NewBotCache.Cache(':memory:')
    # insert server
    insertStatement = """INSERT INTO servers(id, command_prefix, is_locked) VALUES(?,?,?)"""
    cache.createCursor().execute(insertStatement, ("798358551230677042", '!', False))

    # insert roles
    insertStatement = """INSERT INTO privileged_roles(role_id, server_id) VALUES(?,?)"""
    parameters = [(id, "798358551230677042") for id in [
        "805602260993310752",
        "805892126675697686",
        "806302209130102815"
    ]]
    cache.createCursor().executemany(insertStatement, parameters)

    return cache

@pytest.mark.asyncio
async def testAddPrivilegedRole_Single(emptyCache: NewBotCache.Cache):
    expectedDict = [805602260993310752]
    await emptyCache.addPrivilegedRole(798358551230677042, 805602260993310752)
    #assert sorted(emptyCache.privilegedRolesCache) == sorted(expectedDict)
    results = await emptyCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(expectedDict, results)

@pytest.mark.asyncio
async def testAddPrivilegedRole_List(emptyCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
    ]
    await emptyCache.addPrivilegedRole(798358551230677042, [805602260993310752, 805892126675697686, 806302209130102815])
    #assert emptyCache.privilegedRolesCache == expectedDict
    results = await emptyCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddPrivilegedRole_EmptyList(emptyCache: NewBotCache.Cache):
    expectedDict = []
    await emptyCache.addPrivilegedRole(798358551230677042, [])
    #assert emptyCache.privilegedRolesCache == expectedDict
    results = await emptyCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddPrivilegedRole_SingleDuplicate(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
    ]
    await sampleCache.addPrivilegedRole(798358551230677042, 805602260993310752)
    #assert sampleCache.privilegedRolesCache == expectedDict
    results = await sampleCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddPrivilegedRole_ListSingleDuplicate(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815,
            798359230183636994
        ]
    await sampleCache.addPrivilegedRole(798358551230677042, [805602260993310752, 798359230183636994])
    #assert sampleCache.privilegedRolesCache == expectedDict
    results = await sampleCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddPrivilegedRole_ListMultipleDuplicate(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
        
    ]
    await sampleCache.addPrivilegedRole(798358551230677042, [805602260993310752, 805892126675697686, 806302209130102815])
    #assert sampleCache.privilegedRolesCache == expectedDict
    results = await sampleCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddPrivilegedRole_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(IntegrityError):
        await sampleCache.addPrivilegedRole(None, 805602260993310752)
        await sampleCache.addPrivilegedRole(798358551230677042, None)

@pytest.mark.asyncio
async def testAddPrivilegedRole_Incorrect_GuildID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.addPrivilegedRole("Value", 805602260993310752)

@pytest.mark.asyncio
async def testAddPrivilegedRole_Incorrect_RoleID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.addPrivilegedRole(798358551230677042, "Value")
        await sampleCache.addPrivilegedRole(798358551230677042, ["Value", "Value2", "Value3"])

@pytest.mark.asyncio
async def testRemPrivilegedRole_Single(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686
    ]
    await sampleCache.remPrivilegedRole(798358551230677042, 806302209130102815)
    #assert sampleCache.privilegedRolesCache == expectedDict
    results = await sampleCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemPrivilegedRole_List(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752
        
    ]
    await sampleCache.remPrivilegedRole(798358551230677042, [805892126675697686, 806302209130102815])
    #assert sampleCache.privilegedRolesCache == expectedDict
    results = await sampleCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemPrivilegedRole_EmptyList(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
    ]
    await sampleCache.remPrivilegedRole(798358551230677042, [])
    #assert sampleCache.privilegedRolesCache == expectedDict
    results = await sampleCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemPrivilegedRole_NotPresent(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
        
    ]
    await sampleCache.remPrivilegedRole(798358551230677042, 798359230183636994)
    #assert sampleCache.privilegedRolesCache == expectedDict
    results = await sampleCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemPrivilegedRole_SingleItemListNotPresent(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686
        
    ]
    await sampleCache.remPrivilegedRole(798358551230677042, [798359230183636994, 806302209130102815])
    #assert sampleCache.privilegedRolesCache == expectedDict
    results = await sampleCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemPrivilegedRole_MultipleItemListNotPresent(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
        
    ]
    await sampleCache.remPrivilegedRole(798358551230677042, [805919015423443015, 805202898190860348, 805205333613084733])
    #assert sampleCache.privilegedRolesCache == expectedDict
    results = await sampleCache.getServerPrivilegedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemPrivilegedRole_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(IntegrityError):
        await sampleCache.remPrivilegedRole(None, 805602260993310752)
        await sampleCache.remPrivilegedRole(798358551230677042, None)

@pytest.mark.asyncio
async def testRemPrivilegedRole_Incorrect_GuildID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.remPrivilegedRole("Value", 805602260993310752)
        
@pytest.mark.asyncio
async def testRemPrivilegedRole_Incorrect_RoleID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.remPrivilegedRole(798358551230677042, "Value")
        await sampleCache.remPrivilegedRole(798358551230677042, ["Value", "Value2", "Value3"])

