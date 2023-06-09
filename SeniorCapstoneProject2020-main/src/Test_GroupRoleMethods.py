from sqlite3.dbapi2 import IntegrityError
import pytest
import NewBotCache
from collections import Counter

# lambda function for testing equality between unordered lists
compare = lambda x, y: Counter(x) == Counter(y)


## fixtures ##
@pytest.fixture
def emptyCache():
    cache = NewBotCache.Cache(':memory:')

    # insert server
    insertStatement = """INSERT INTO servers(id, command_prefix, is_locked) VALUES(?,?,?)"""
    cache.dbConnection.execute(insertStatement, (798358551230677042,'!',False))

    return cache

@pytest.fixture
def sampleCache():
    cache = NewBotCache.Cache(':memory:')
    # insert server
    insertStatement = """INSERT INTO servers(id, command_prefix, is_locked) VALUES(?,?,?)"""
    cache.dbConnection.execute(insertStatement, ("798358551230677042",'!',False))

    # insert roles
    insertStatement = """INSERT INTO groups(role_id, server_id, category_id) VALUES(?,?,?)"""
    parameters = [(id, "798358551230677042", cat_id) for id, cat_id in zip(
        [
            "805602260993310752",
            "805892126675697686",
            "806302209130102815"
        ],
        [
            "834165166769307678",
            "834165167528607784",
            "834165168102440990"
        ]
    )]
    cache.dbConnection.executemany(insertStatement, parameters)

    return cache


## unit tests ##
@pytest.mark.asyncio
async def testAddGroupRole_Single(emptyCache: NewBotCache.Cache):
    expectedResults = [805602260993310752]
    await emptyCache.addGroupRole(798358551230677042, 805602260993310752, 834165166769307678)
    results = await emptyCache.getServerGroupRolesList(798358551230677042)
    assert compare(expectedResults, results)

@pytest.mark.asyncio
async def testAddGroupRole_List(emptyCache: NewBotCache.Cache):
    expectedResults = [805602260993310752,
                       805892126675697686,
                       806302209130102815]
    await emptyCache.addGroupRole(798358551230677042, [805602260993310752, 805892126675697686, 806302209130102815], [834165166769307678, 834165167528607784, 834165168102440990])
    results = await emptyCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testAddGroupRole_EmptyList(emptyCache: NewBotCache.Cache):
    expectedResults = []
    await emptyCache.addGroupRole(798358551230677042, [], [])
    results = await emptyCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testAddGroupRole_SingleDuplicate(sampleCache: NewBotCache.Cache):
    expectedResults = [805602260993310752,
                       805892126675697686,
                       806302209130102815]
    await sampleCache.addGroupRole(798358551230677042, 805602260993310752, 834165166769307678)
    results = await sampleCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testAddGroupRole_ListSingleDuplicate(sampleCache: NewBotCache.Cache):
    expectedResults = [805602260993310752,
                       805892126675697686,
                       806302209130102815,
                       798359230183636994]
    await sampleCache.addGroupRole(798358551230677042, [805602260993310752, 798359230183636994], [834165166769307678, 834165167528607784])
    results = await sampleCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testAddGroupRole_ListMultipleDuplicate(sampleCache: NewBotCache.Cache):
    expectedResults = [805602260993310752,
                       805892126675697686,
                       806302209130102815]
    await sampleCache.addGroupRole(798358551230677042, [805602260993310752, 805892126675697686, 806302209130102815], [834165166769307678, 834165167528607784, 834165168102440990])
    results = await sampleCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

# Type testing unit tests
@pytest.mark.asyncio
async def testAddGroupRole_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(IntegrityError):
        await sampleCache.addGroupRole(None, 805602260993310752, 834165166769307678)
        await sampleCache.addGroupRole(798358551230677042, None, 834165166769307678)

@pytest.mark.asyncio
async def testAddGroupRole_Incorrect_GuildID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.addGroupRole("Value", 805602260993310752, 834165166769307678)

@pytest.mark.asyncio
async def testAddGroupRole_Incorrect_RoleID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.addGroupRole(798358551230677042, "Value", 834165166769307678)
        await sampleCache.addGroupRole(798358551230677042, ["Value", "Value2", "Value3"], [834165166769307678, 834165167528607784, 834165168102440990])

@pytest.mark.asyncio
async def testRemGroupRole_Single(sampleCache: NewBotCache.Cache):
    expectedResults = [805602260993310752,
                       805892126675697686]
    await sampleCache.remGroupRole(798358551230677042, 806302209130102815)
    results = await sampleCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testRemGroupRole_List(sampleCache: NewBotCache.Cache):
    expectedResults = [805602260993310752]
    await sampleCache.remGroupRole(798358551230677042, [805892126675697686, 806302209130102815])
    results = await sampleCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testRemGroupRole_EmptyList(sampleCache: NewBotCache.Cache):
    expectedResults = [805602260993310752,
                       805892126675697686,
                       806302209130102815]
    await sampleCache.remGroupRole(798358551230677042, [])
    results = await sampleCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testRemGroupRole_NotPresent(sampleCache: NewBotCache.Cache):
    expectedResults = [805602260993310752,
                       805892126675697686,
                       806302209130102815]
    await sampleCache.remGroupRole(798358551230677042, 798359230183636994)
    results = await sampleCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testRemGroupRole_SingleItemListNotPresent(sampleCache: NewBotCache.Cache):
    expectedResults = [805602260993310752,
                       805892126675697686]
    await sampleCache.remGroupRole(798358551230677042, [798359230183636994, 806302209130102815])
    results = await sampleCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testRemGroupRole_MultipleItemListNotPresent(sampleCache: NewBotCache.Cache):
    expectedResults = [805602260993310752,
                       805892126675697686,
                       806302209130102815]
    await sampleCache.remGroupRole(798358551230677042, [805919015423443015, 805202898190860348, 805205333613084733])
    results = await sampleCache.getServerGroupRolesList(798358551230677042)
    assert compare(results, expectedResults)

@pytest.mark.asyncio
async def testRemGroupRole_None(sampleCache: NewBotCache.Cache):
    with pytest.raises(IntegrityError):
        await sampleCache.remGroupRole(None, 805602260993310752)
        await sampleCache.remGroupRole(798358551230677042, None)

@pytest.mark.asyncio
async def testRemGroupRole_Incorrect_GuildID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.remGroupRole("Value", 805602260993310752)

@pytest.mark.asyncio
async def testRemGroupRole_Incorrect_RoleID(sampleCache: NewBotCache.Cache):
    with pytest.raises(TypeError):
        await sampleCache.remGroupRole(798358551230677042, "Value")
        await sampleCache.remGroupRole(798358551230677042, ["Value", "Value2", "Value3"])

@pytest.mark.asyncio
async def testIsGroupRole_GroupRole(sampleCache: NewBotCache.Cache):
    result = await sampleCache.isGroupRole(798358551230677042, 805602260993310752)
    assert result

@pytest.mark.asyncio
async def testIsGroupRole_NotGroupRole(sampleCache: NewBotCache.Cache):
    result = await sampleCache.isGroupRole(798358551230677042, 805602260993310751)
    assert not result