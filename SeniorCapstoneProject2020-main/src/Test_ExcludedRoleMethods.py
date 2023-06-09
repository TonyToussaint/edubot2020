import pytest
import NewBotCache
from collections import Counter
from sqlite3.dbapi2 import IntegrityError


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
    insertStatement = """INSERT INTO excluded_roles(role_id, server_id) VALUES(?,?)"""
    parameters = [(id, "798358551230677042") for id in [
        "805602260993310752",
        "805892126675697686",
        "806302209130102815"
    ]]
    cache.createCursor().executemany(insertStatement, parameters)

    return cache


@pytest.mark.asyncio
async def testAddExcludedRole_Single(emptyCache: NewBotCache.Cache):
    expectedDict = [805602260993310752]
    await emptyCache.addExcludedRole(798358551230677042, 805602260993310752)
    #assert emptyCache.excludedRolesCache == expectedDict
    results = await emptyCache.getServerExcludedRolesList(798358551230677042)
    assert compare(expectedDict, results)

@pytest.mark.asyncio
async def testAddExcludedRole_List(emptyCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815]

    await emptyCache.addExcludedRole(798358551230677042, [805602260993310752, 805892126675697686, 806302209130102815])
    #assert emptyCache.excludedRolesCache == expectedDict
    results = await emptyCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddExcludedRole_EmptyList(emptyCache: NewBotCache.Cache):
    expectedDict = []
    await emptyCache.addExcludedRole(798358551230677042, [])
    results = await emptyCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddExcludedRole_SingleDuplicate(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
    ]
    await sampleCache.addExcludedRole(798358551230677042, 805602260993310752)
    #assert sampleCache.excludedRolesCache == expectedDict
    results = await sampleCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddExcludedRole_ListSingleDuplicate(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815,
            798359230183636994
        ]
    await sampleCache.addExcludedRole(798358551230677042, [805602260993310752, 798359230183636994])
    #assert sampleCache.excludedRolesCache == expectedDict
    results = await sampleCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddExcludedRole_ListMultipleDuplicate(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815]
    await sampleCache.addExcludedRole(798358551230677042, [805602260993310752, 805892126675697686, 806302209130102815])
    #assert sampleCache.excludedRolesCache == expectedDict
    results = await sampleCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testAddExcludedRole_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(IntegrityError):
        await sampleCache.addExcludedRole(None, 805602260993310752)
        await sampleCache.addExcludedRole(798358551230677042, None)

@pytest.mark.asyncio
async def testAddExcludedRole_Incorrect_GuildID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.addExcludedRole("Value", 805602260993310752)

@pytest.mark.asyncio
async def testAddExcludedRole_Incorrect_RoleID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.addExcludedRole(798358551230677042, "Value")
        await sampleCache.addExcludedRole(798358551230677042, ["Value", "Value2", "Value3"])


@pytest.mark.asyncio
async def testRemExcludedRole_Single(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686
    ]
    await sampleCache.remExcludedRole(798358551230677042, 806302209130102815)
    #assert sampleCache.excludedRolesCache == expectedDict
    results = await sampleCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemExcludedRole_List(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752
    ]
    await sampleCache.remExcludedRole(798358551230677042, [805892126675697686, 806302209130102815])
    #assert sampleCache.excludedRolesCache == expectedDict
    results = await sampleCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemExcludedRole_EmptyList(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
    ]
    
    await sampleCache.remExcludedRole(798358551230677042, [])
    #assert sampleCache.excludedRolesCache == expectedDict
    results = await sampleCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemExcludedRole_NotPresent(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
    ]
    await sampleCache.remExcludedRole(798358551230677042, 798359230183636994)
    #assert sampleCache.excludedRolesCache == expectedDict
    results = await sampleCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemExcludedRole_SingleItemListNotPresent(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686
    ]
    await sampleCache.remExcludedRole(798358551230677042, [798359230183636994, 806302209130102815])
    #assert sampleCache.excludedRolesCache == expectedDict
    results = await sampleCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemExcludedRole_MultipleItemListNotPresent(sampleCache: NewBotCache.Cache):
    expectedDict = [
            805602260993310752,
            805892126675697686,
            806302209130102815
    ]
    await sampleCache.remExcludedRole(798358551230677042, [805919015423443015, 805202898190860348, 805205333613084733])
    #assert sampleCache.excludedRolesCache == expectedDict
    results = await sampleCache.getServerExcludedRolesList(798358551230677042)
    assert compare(results, expectedDict)

@pytest.mark.asyncio
async def testRemExcludedRole_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(IntegrityError):
        await sampleCache.remExcludedRole(None, 805602260993310752)
        await sampleCache.remExcludedRole(798358551230677042, None)

@pytest.mark.asyncio
async def testRemExcludedRole_Incorrect_GuildID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.remExcludedRole("Value", 805602260993310752)
        
@pytest.mark.asyncio
async def testAddExcludedRole_Incorrect_RoleID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.remExcludedRole(798358551230677042, "Value")
        await sampleCache.remExcludedRole(798358551230677042, ["Value", "Value2", "Value3"])