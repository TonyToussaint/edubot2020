"""Module contains Cache class for interacting with local cache database."""

import sqlite3
import discord
from discord.ext import commands, tasks
from typing import Union, Optional, List, Tuple

class Cache():
    """Cache object stores object references for local cache database and methods for abstracting
    data modification and data retrieval from the database.
    """
    def __init__(self, dbFile: str):
        self.dbConnection = self.createConnection(dbFile)
        if (self.dbConnection is not None):
            self.initializeDatabase()


    ###### DATABASE INITIALIZATION ######
    def createConnection(self, dbFile: str):
        """Create connection to the SQLite database, creating the db file if it doesn't
        already exist and returning the connection object
        """
        dbConnection = None
        try:
            dbConnection = sqlite3.connect(dbFile)
        except sqlite3.Error as e:
            print(e)
            print(f"Database connection to '{dbFile}' failed, terminating...")
            exit()
            
        dbConnection.execute("PRAGMA foreign_keys = 1")
        dbConnection.commit()
        return dbConnection

    def createCursor(self):
        """Gets a cursor object for the current db connection and returns it
        """
        dbCursor = None
        try:
            dbCursor = self.dbConnection.cursor()
        except sqlite3.Error as e:
            print(e)
        finally:
            return dbCursor

    def initializeDatabase(self):
        """Initialize tables in the db file if they do not already exist
        """

        # store table creation statements and pass each of them to createTable
        sqlCreateTableServers = """CREATE TABLE IF NOT EXISTS servers (
            id text PRIMARY KEY ON CONFLICT IGNORE,
            command_prefix text NOT NULL,
            infraction_channel text,
            notification_channel text,
            is_locked int NOT NULL
        );"""

        sqlCreateTableGroups = """CREATE TABLE IF NOT EXISTS groups (
            role_id text PRIMARY KEY ON CONFLICT IGNORE,
            server_id text NOT NULL,
            category_id text NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        );"""

        sqlCreateTablePrivilegedRoles = """CREATE TABLE IF NOT EXISTS privileged_roles (
            role_id text PRIMARY KEY ON CONFLICT IGNORE,
            server_id text NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        );"""

        sqlCreateTableExcludedRoles = """CREATE TABLE IF NOT EXISTS excluded_roles (
            role_id text PRIMARY KEY ON CONFLICT IGNORE,
            server_id text NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        );"""

        sqlCreateTablePermOverwrites = """CREATE TABLE IF NOT EXISTS perm_overwrites (
            channel_id text NOT NULL,
            modified_id text NOT NULL,
            server_id text NOT NULL,
            allow_value text NOT NULL,
            deny_value text NOT NULL,
            CONSTRAINT PK_PermOverwrite PRIMARY KEY (channel_id,modified_id) ON CONFLICT REPLACE
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        );"""

        sqlCreateTablePolls = """CREATE TABLE IF NOT EXISTS polls (
            poll_id text NOT NULL,
            server_id text NOT NULL,
            channel_id text NOT NULL,
            message_id text NOT NULL UNIQUE,
            questions text NOT NULL,
            CONSTRAINT PK_Poll PRIMARY KEY (poll_id, message_id),
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        );"""

        sqlCreateTableRoleReactMsgs = """CREATE TABLE IF NOT EXISTS role_react_msgs (
            message_id text PRIMARY KEY,
            channel_id text NOT NULL,
            server_id text NOT NULL,
            role_id text NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        );"""

        sqlCreateTableRoleInvites = """CREATE TABLE IF NOT EXISTS role_invites (
            invite_id text PRIMARY KEY,
            server_id text NOT NULL,
            role_id text NOT NULL,
            uses_count int NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
        );"""

        with self.dbConnection:
            self.createTable(sqlCreateTableServers)
            self.createTable(sqlCreateTableGroups)
            self.createTable(sqlCreateTablePrivilegedRoles)
            self.createTable(sqlCreateTableExcludedRoles)
            self.createTable(sqlCreateTablePermOverwrites)
            self.createTable(sqlCreateTablePolls)
            self.createTable(sqlCreateTableRoleReactMsgs)
            self.createTable(sqlCreateTableRoleInvites)

    def createTable(self, sqlCreateTable):
        """Creates a table based on the definition given in parameter sqlCreateTable
        """
        try:
            cursor = self.createCursor()
            cursor.execute(sqlCreateTable)
        except sqlite3.Error as e:
            print(e)


    #### CACHE MODIFICATION METHODS ####
    ## servers table methods ##
    async def addServer(self, guildID: int):
        """Add new row for a server in the servers table of the local cache database, 
        initializing the server settings to their default values.
        """
        if (guildID is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(guildID, int)):
            raise TypeError

        cursor = self.createCursor()
        insertStatement = """INSERT INTO servers(id, command_prefix, is_locked) VALUES(?,?,?)"""

        with self.dbConnection:
            cursor.execute(insertStatement, (str(guildID), '!', 0))

    async def remServer(self, guildID: int):
        """Remove a row for a server from the servers table in local cache database.
        """
        if (not isinstance(guildID, int)):
            raise TypeError

        cursor = self.createCursor()
        deleteStatement = """DELETE FROM servers WHERE id = ?"""

        with self.dbConnection:
            cursor.execute(deleteStatement, (str(guildID),))

    async def getServerCommandPrefix(self, guildID: int):
        """Returns the command prefix character for the given server. If server is not in database
        for some reason, adds it to database and returns default prefix ('!').
        """
        if (not isinstance(guildID, int)):
            raise TypeError

        cursor = self.createCursor()
        selectStatement = """SELECT command_prefix FROM servers WHERE id = ?"""

        cursor.execute(selectStatement, (str(guildID),))

        # check if server lookup returns anything, if not, add server to db
        # this shouldn't happen normally, but will catch it if it does
        try:
            prefix, = cursor.fetchone()
            return prefix
        except TypeError:
            await self.addServer(guildID)
            return '!'

    async def setServerCommandPrefix(self, guildID: int, newPrefix: str):
        """Modifies the command prefix character for the given server. Returns bool indicating
        whether update was successful or not.
        """
        if (not isinstance(guildID, int)):
            raise TypeError
        elif (newPrefix is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(newPrefix, str)):
            raise TypeError
        elif (len(newPrefix) != 1):
            raise commands.errors.BadArgument

        cursor = self.createCursor()
        updateStatement = """UPDATE servers SET command_prefix = ? WHERE id = ?"""

        with self.dbConnection:
            cursor.execute(updateStatement, (newPrefix, str(guildID)))

        return cursor.rowcount == 1
    
    async def getServerLockStatus(self, guildID: int):
        """Returns the lock status for the given server.
        """
        if (not isinstance(guildID, int)):
            raise TypeError

        cursor = self.createCursor()
        selectStatement = """SELECT is_locked FROM servers WHERE id = ?"""

        cursor.execute(selectStatement, (str(guildID),))

        try:
            lockStatus, = cursor.fetchone()
            return lockStatus == 1
        except TypeError:
            return None

    async def setServerLockStatus(self, guildID: int, lockStatus: bool):
        """Modifies the lock status of the given server.
        """
        if (not isinstance(guildID, int)):
            raise TypeError
        elif (lockStatus is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(lockStatus, bool)):
            raise TypeError
               
        cursor = self.createCursor()
        updateStatement = """UPDATE servers SET is_locked = ? WHERE id = ?"""

        with self.dbConnection:
            lockVal = 1 if lockStatus else 0
            cursor.execute(updateStatement, (lockVal, str(guildID)))

    async def getServerInfractionChannelID(self, guildID: int):
        """Returns the id number of the infraction channel for the given server. Returns
        None if no channel_id is stored for infraction channel.
        """
        if (not isinstance(guildID, int)):
            raise TypeError

        cursor = self.createCursor()
        selectStatement = """SELECT infraction_channel FROM servers WHERE id = ?"""

        cursor.execute(selectStatement, (str(guildID),))

        try:
            infractionChannelID, = cursor.fetchone()
            return int(infractionChannelID)
        except TypeError:
            return None
        except ValueError:
            return None

    async def setServerInfractionChannelID(self, guildID: int, channelID: Optional[int]):
        """Modifies the channel id of the infraction channel for the given server
        in the database.
        """
        if (not isinstance(guildID, int)):
            raise TypeError
        elif (not isinstance(channelID, int) and channelID is not None):
            raise TypeError

        cursor = self.createCursor()
        updateStatement = """UPDATE servers SET infraction_channel = ? WHERE id = ?"""

        with self.dbConnection:
            cursor.execute(updateStatement, (str(channelID), str(guildID)))

    async def getServerNotificationChannelID(self, guildID: int):
        """Returns the id number of the notification channel for the given server. Returns
        None if no channel_id is stored for notification channel.
        """
        if (not isinstance(guildID, int)):
            raise TypeError

        cursor = self.createCursor()
        selectStatement = """SELECT notification_channel FROM servers WHERE id = ?"""

        cursor.execute(selectStatement, (str(guildID),))

        try:
            notificationChannelID, = cursor.fetchone()
            return int(notificationChannelID)
        except TypeError:
            return None
        except ValueError:
            return None

    async def setServerNotificationChannelID(self, guildID: int, channelID: Optional[int]):
        """Modifies the channel if of the notification channel for the given server
        in the database.
        """
        if (not isinstance(guildID, int)):
            raise TypeError
        elif (not isinstance(channelID, int) and channelID is not None):
            raise TypeError

        cursor = self.createCursor()
        updateStatement = """UPDATE servers SET notification_channel = ? WHERE id = ?"""

        with self.dbConnection:
            cursor.execute(updateStatement, (str(channelID), str(guildID)))


    ## groups table methods ##
    async def addGroupRole(self, guildID: int, roleIDs: Union[int, List[int]], categoryIDs: Union[int, List[int]]):
        """Add new rows for group roles into the groups table of the local cache
        \n:param:`roleIDs` can be either a single new entry or list of new entries
        """
        # type checking
        if (guildID is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(guildID, int)):
            raise TypeError
        elif (roleIDs is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(roleIDs, int) and not isinstance(roleIDs, list)):
            raise TypeError
        elif (not isinstance(categoryIDs, int) and not isinstance(categoryIDs, list)):
            raise TypeError
        elif (type(roleIDs) != type(categoryIDs)):
            raise TypeError

        cursor = self.createCursor()
        insertStatement = """INSERT INTO groups(role_id, server_id, category_id) VALUES(?,?,?)"""

        # determine whether the method was passed a single role or a list of roles
        # and either insert a single entry or a list of entries
        if isinstance(roleIDs, int):
            cursor.execute(insertStatement, (str(roleIDs), str(guildID), str(categoryIDs)))
        else:
            # check typing on parameters before begining list operations
            if (not all([isinstance(roleID, int) for roleID in roleIDs])):
                raise TypeError
            if (not all([isinstance(categoryID, int) for categoryID in categoryIDs])):
                raise TypeError
            if (len(roleIDs) != len(categoryIDs)):
                raise TypeError
            
            parameters = [(str(roleID), str(guildID), str(categoryID)) for roleID, categoryID in zip(roleIDs, categoryIDs)]
            cursor.executemany(insertStatement, parameters)

    async def remGroupRole(self, guildID: int, roleIDs: Union[int, List[int]]):
        """Removes rows from groups table in the local cache
        \n:param:`roleIDs` can be either a single role or list of roles to remove
        """
        # type checking
        if (guildID is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(guildID, int)):
            raise TypeError
        elif (roleIDs is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(roleIDs, int) and not isinstance(roleIDs, list)):
            raise TypeError

        cursor = self.createCursor()
        deleteStatement = """DELETE FROM groups WHERE role_id = ? AND server_id = ?"""

        # determine whether the method was passed a single role or a list of roles
        # and either delete a single entry or a list of entries
        if isinstance(roleIDs, int):
            cursor.execute(deleteStatement, (str(roleIDs), str(guildID)))
        else:
            # return TypeError if not all roleIDs are integers
            if (not all([isinstance(roleID, int) for roleID in roleIDs])):
                raise TypeError

            parameters = [(str(roleID), str(guildID)) for roleID in roleIDs]
            cursor.executemany(deleteStatement, parameters)

    async def isGroupRole(self, guildID: int, roleID: int):
        """Checks the group roles table to see if the given role is a group role
        on the given server. If the role is present in the table, returns true 
        indicating the role is a group role, else returns false indicating that it is not.
        """
        # type checking
        if (not isinstance(guildID, int) or not isinstance(roleID, int)):
            raise TypeError

        # get the row count when searching for a specific role on a server, if row count
        # is 1, then return true, else if row count is 0, then return false
        cursor = self.createCursor()
        selectStatement = """SELECT COUNT(1) FROM groups WHERE server_id = ? AND role_id = ?"""

        cursor.execute(selectStatement, (str(guildID), str(roleID)))
        result, = cursor.fetchone()
        if (result > 0):
            return True
        else:
            return False

    async def getServerGroupRolesList(self, guildID: int):
        """Returns list of group roles existing on the given server.
        """
        # type checking
        if (not isinstance(guildID, int)):
            raise TypeError

        # select all group role IDs on a given server and place them into an iterator
        cursor = self.createCursor()
        selectStatement = """SELECT role_id FROM groups WHERE server_id = ?"""

        cursor.execute(selectStatement, (guildID,))

        try:
            groupList = [int(row[0]) for row in cursor]
            return groupList
        except TypeError:
            return None

    async def getGroupCategoryChannelID(self, guildID: int, roleID: int):
        """Returns the channel ID of the category channel corresponding to a specific group role. Returns
        None if role is not a group role.
        """
        cursor = self.createCursor()
        selectStatement = """SELECT category_id FROM groups WHERE server_id = ? AND role_id = ?"""

        cursor.execute(selectStatement, (str(guildID), str(roleID)))

        result = cursor.fetchone()
        if (result is not None):
            categoryID, = result
            return int(categoryID)
        else:
            return None


    ## privileged_roles table methods ##
    async def addPrivilegedRole(self, guildID: int, roleIDs: Union[int, List[int]]):
        """Add new rows for group roles into the privileged_roles table of the local cache
        \n:param:`roleIDs` can be either a single new entry or list of new entries
        """
        # type checking
        if (guildID is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(guildID, int)):
            raise TypeError
        elif (roleIDs is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(roleIDs, int) and not isinstance(roleIDs, list)):
            raise TypeError

        cursor = self.createCursor()
        insertStatement = """INSERT INTO privileged_roles(role_id, server_id) VALUES(?,?)"""

        # determine whether the method was passed a single role or a list of roles
        # and either insert a single entry or a list of entries
        with self.dbConnection:
            if isinstance(roleIDs, int):
                cursor.execute(insertStatement, (str(roleIDs), str(guildID)))
            else:
                # return TypeError if not all roleIDs are integers
                if (not all([isinstance(roleID, int) for roleID in roleIDs])):
                    raise TypeError

                parameters = [(str(roleID), str(guildID)) for roleID in roleIDs]
                cursor.executemany(insertStatement, parameters)

    async def remPrivilegedRole(self, guildID: int, roleIDs: Union[int, List[int]]):
        """Removes rows from privileged_roles table in the local cache
        \n:param:`roleIDs` can be either a single role or list of roles to remove
        """
        # type checking
        if (guildID is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(guildID, int)):
            raise TypeError
        elif (roleIDs is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(roleIDs, int) and not isinstance(roleIDs, list)):
            raise TypeError

        cursor = self.createCursor()
        deleteStatement = """DELETE FROM privileged_roles WHERE role_id = ? AND server_id = ?"""

        # determine whether the method was passed a single role or a list of roles
        # and either delete a single entry or a list of entries
        with self.dbConnection:
            if isinstance(roleIDs, int):
                cursor.execute(deleteStatement, (str(roleIDs), str(guildID)))
            else:
                # return TypeError if not all roleIDs are integers
                if (not all([isinstance(roleID, int) for roleID in roleIDs])):
                    raise TypeError

                parameters = [(str(roleID), str(guildID)) for roleID in roleIDs]
                cursor.executemany(deleteStatement, parameters)

    async def isPrivilegedRole(self, guildID: int, roleID: int):
        """Checks the privileged_roles table to see if the given role is a privileged role
        on the given server. If the role is present in the table, returns true 
        indicating the role is a privileged role, else returns false indicating that it is not.
        """
        # type checking
        if (not isinstance(guildID, int) or not isinstance(roleID, int)):
            raise TypeError

        # get the row count when searching for a specific role on a server, if row count
        # is 1, then return true, else if row count is 0, then return false
        cursor = self.createCursor()
        selectStatement = """SELECT COUNT(1) FROM privileged_roles WHERE server_id = ? AND role_id = ?"""

        cursor.execute(selectStatement, (str(guildID), str(roleID)))
        result, = cursor.fetchone()
        if (result > 0):
            return True
        else:
            return False

    async def getServerPrivilegedRolesList(self, guildID: int):
        """Returns list of privileged roles existing on the given server.
        """
        # type checking
        if (not isinstance(guildID, int)):
            raise TypeError

        # select all group role IDs on a given server and place them into an iterator
        cursor = self.createCursor()
        selectStatement = """SELECT role_id FROM privileged_roles WHERE server_id = ?"""

        cursor.execute(selectStatement, (guildID,))

        try:
            privilegedList = [int(row[0]) for row in cursor]
            return privilegedList
        except TypeError:
            return None


    ## excluded_roles table methods ##
    async def addExcludedRole(self, guildID: int, roleIDs: Union[int, List[int]]):
        """Add new rows for group roles into the excluded_roles table of the local cache
        \n:param:`roleIDs` can be either a single new entry or list of new entries
        """
        # type checking
        if (guildID is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(guildID, int)):
            raise TypeError
        elif (roleIDs is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(roleIDs, int) and not isinstance(roleIDs, list)):
            raise TypeError

        cursor = self.createCursor()
        insertStatement = """INSERT INTO excluded_roles(role_id, server_id) VALUES(?,?)"""

        # determine whether the method was passed a single role or a list of roles
        # and either insert a single entry or a list of entries
        with self.dbConnection:
            if isinstance(roleIDs, int):
                cursor.execute(insertStatement, (str(roleIDs), str(guildID)))
            else:
                # return TypeError if not all roleIDs are integers
                if (not all([isinstance(roleID, int) for roleID in roleIDs])):
                    raise TypeError

                parameters = [(str(roleID), str(guildID)) for roleID in roleIDs]
                cursor.executemany(insertStatement, parameters)

    async def remExcludedRole(self, guildID: int, roleIDs: Union[int, List[int]]):
        """Removes rows from excluded_roles table in the local cache
        \n:param:`roleIDs` can be either a single role or list of roles to remove
        """
        # type checking
        if (guildID is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(guildID, int)):
            raise TypeError
        elif (roleIDs is None):
            raise sqlite3.IntegrityError
        elif (not isinstance(roleIDs, int) and not isinstance(roleIDs, list)):
            raise TypeError

        cursor = self.createCursor()
        deleteStatement = """DELETE FROM excluded_roles WHERE role_id = ? AND server_id = ?"""

        # determine whether the method was passed a single role or a list of roles
        # and either delete a single entry or a list of entries
        with self.dbConnection:
            if isinstance(roleIDs, int):
                cursor.execute(deleteStatement, (str(roleIDs), str(guildID)))
            else:
                # return TypeError if not all roleIDs are integers
                if (not all([isinstance(roleID, int) for roleID in roleIDs])):
                    raise TypeError

                parameters = [(str(roleID), str(guildID)) for roleID in roleIDs]
                cursor.executemany(deleteStatement, parameters)

    async def isExcludedRole(self, guildID: int, roleID: int):
        """Checks the excluded_roles table to see if the given role is a excluded role
        on the given server. If the role is present in the table, returns true 
        indicating the role is a excluded role, else returns false indicating that it is not.
        """
        # type checking
        if (not isinstance(guildID, int) or not isinstance(roleID, int)):
            raise TypeError

        # get the row count when searching for a specific role on a server, if row count
        # is 1, then return true, else if row count is 0, then return false
        cursor = self.createCursor()
        selectStatement = """SELECT COUNT(1) FROM excluded_roles WHERE server_id = ? AND role_id = ?"""

        cursor.execute(selectStatement, (str(guildID), str(roleID)))
        result, = cursor.fetchone()
        if (result > 0):
            return True
        else:
            return False

    async def getServerExcludedRolesList(self, guildID: int):
        """Returns list of excluded roles existing on the given server.
        """
        # type checking
        if (not isinstance(guildID, int)):
            raise TypeError

        # select all group role IDs on a given server and place them into an iterator
        cursor = self.createCursor()
        selectStatement = """SELECT role_id FROM excluded_roles WHERE server_id = ?"""

        cursor.execute(selectStatement, (guildID,))

        try:
            excludedList = [int(row[0]) for row in cursor]
            return excludedList
        except TypeError:
            return None


    ## perm_overwrites table methods ##
    async def addPermOverwrite(self, guildID: int, channelID: int, modifiedID: int, overwrite: discord.PermissionOverwrite):
        """Add new row for a permission overwrite to the permOverwrite table of the local cache. Attempting to add
        a new row for a channel and modified id pair already in db, the previous overwrite value will be replaced.
        \n:param:`modifiedID` is either a role or user ID number corresponding to the role or user that a
        permission overwrite applies to.
        """
        # insert row into permOverwrite table with the supplied data, converting the
        # PermissionOverwrite object into a pair of values corresponding to the numeric
        # representation of its allowed permissions and denied permissions
        cursor = self.createCursor()
        insertStatement = """INSERT INTO perm_overwrites(channel_id, modified_id, server_id, allow_value, deny_value)
        VALUES(?,?,?,?,?)"""

        allow, deny = overwrite.pair()

        with self.dbConnection:
            try:
                cursor.execute(insertStatement, (str(channelID), str(modifiedID), str(guildID), str(allow.value), str(deny.value)))
            except sqlite3.IntegrityError:
                # if entry already exists in db, update entry rather than inserting it
                updateStatement = """UPDATE perm_overwrites SET allow_value = ?, deny_value = ?
                WHERE guildID = ? AND channel_id = ? AND modified_id = ?"""
                cursor.execute(updateStatement, (str(allow), str(deny), str(guildID), str(channelID), str(modifiedID)))

    async def remPermOverwrite(self, guildID: int, channelID: Optional[int] = None, modifiedID: Optional[int] = None):
        """Removes row from permOverwrite table of local cache. Providing each level of specificity
        will filter the entries removed further, from deleting all entries for a server down to deleting
        a specific entry.
        \n:param:`modifiedID` is either a role or user ID number corresponding to the role or user that a
        permission overwrite applies to. 
        """
        # check each level of specificity given, and remove the most specific entry provided
        cursor = self.createCursor()
        deleteStatement = """DELETE FROM perm_overwrites WHERE server_id = ?"""
        parameters = (str(guildID),)

        if (channelID is not None):
            deleteStatement += "AND channel_id = ?"
            parameters += (str(channelID),)

        if (modifiedID is not None):
            deleteStatement += "AND modified_id = ?"
            parameters += (str(modifiedID),)

        with self.dbConnection:
            cursor.execute(deleteStatement, parameters)

    async def getPermOverwrite(self, guildID: int, channelID: int, modifiedID: int):
        """Returns a PermissionOverwrite object based on the stored allow/deny value pair corresponding
        to the given guild, channel, and role/user ID number provided, or None if no overwrite exists.
        \n:param:`modifiedID` is either a role or user ID number corresponding to the role or user that a
        permission overwrite applies to. 
        """
        # get the allow deny pair corresponding to the given parameters and create a PermissionOverwrite
        # object from the pair
        cursor = self.createCursor()
        selectStatement = """SELECT allow_value, deny_value FROM perm_overwrites 
        WHERE server_id = ? AND channel_id = ? AND modified_id = ?"""

        cursor.execute(selectStatement, (str(guildID), str(channelID), str(modifiedID)))

        # return none if no overwrite was found, else construct and return an overwrite object
        try:
            allow_val, deny_val = cursor.fetchone()
            allow = discord.Permissions(int(allow_val))
            deny = discord.Permissions(int(deny_val))
            overwrite = discord.PermissionOverwrite.from_pair(allow, deny)
            return overwrite
        except TypeError:
            return None

    async def getChannelOverwritesList(self, guildID: int, channelID: int):
        """Retrieve list of tuples containing a modified id and an associated permission overwrite.
        """
        cursor = self.createCursor()
        selectStatement = """SELECT modified_id, allow_value, deny_value FROM perm_overwrites WHERE server_id = ? AND channel_id = ?"""

        cursor.execute(selectStatement, (str(guildID), str(channelID)))

        try:
            results = cursor.fetchall()
            channelOverwrites = [(int(modifiedID), discord.PermissionOverwrite.from_pair(discord.Permissions(int(allowVal)), discord.Permissions(int(denyVal))))\
                for modifiedID, allowVal, denyVal in results]
        except TypeError:
            return None

        return channelOverwrites

    async def updateOverwriteChannel(self, guildID: int, oldChannelID: int, newChannelID: int):
        """Update the rows in the perm_overwrites table with a given channel ID to a new channel ID.
        Use in the event that a channel gets recreated during a deleteMSG all.
        """
        cursor = self.createCursor()
        updateStatement = """UPDATE perm_overwrites SET channel_id = ? WHERE server_id = ? AND channel_id = ?"""

        with self.dbConnection:
            cursor.execute(updateStatement, (str(newChannelID), str(guildID), str(oldChannelID)))


    ## polls table methods ##
    async def addPoll(self, guildID: int, message: discord.Message, questions: List[str]):
        """Takes the guild ID of the server and a message object and creates a row pertaining
        to the poll in the local cache database.
        """
        cursor = self.createCursor()
        pollSelectStatement = """SELECT poll_id FROM polls WHERE server_id = ?"""
        insertStatement = """INSERT INTO polls(poll_id, server_id, channel_id, message_id, questions) VALUES(?,?,?,?,?)"""

        # create a unique 5 digit poll id by getting the last 5 digits of the product of
        # the message's id and the message channel's id
        pollID = (message.id * message.channel.id) % 100000
        cursor.execute(pollSelectStatement, (str(guildID),))
        guildPolls = cursor.fetchall()

        # check if the pollID is already present in server poll list, if so increment the id
        # until it does not match any existing id on this server
        while((str(pollID).zfill(5),) in guildPolls):
            pollID += 1
            if (pollID == 100000):
                pollID = 0

        pollID = str(pollID).zfill(5)

        # concatenate questions into a single ASCII-001 delimited string, stripping any instance
        # of the character from the questions first to avoid any unexpected errors
        questions = [q.replace(chr(1), "") for q in questions]
        questionString = chr(1).join(questions)

        with self.dbConnection:
            cursor.execute(insertStatement, (pollID, str(guildID), str(message.channel.id), str(message.id), questionString))

        return pollID

    async def remPoll(self, guildID: int, pollID: str):
        """Removes row in polls table of local cache corresponding to the given pollID
        on the given server.
        """
        if (not pollID.isnumeric()):
            raise ValueError

        cursor = self.createCursor()
        deleteStatement = """DELETE FROM polls WHERE server_id = ? AND poll_id = ?"""

        with self.dbConnection:
            cursor.execute(deleteStatement, (str(guildID), pollID))

    async def prunePolls(self, guildID: int, channelID: int):
        """Removes all database entries for polls in a given channel.
        """
        cursor = self.createCursor()
        deleteStatement = """DELETE FROM polls WHERE server_id = ? AND channel_id = ?"""

        with self.dbConnection:
            cursor.execute(deleteStatement, (str(guildID), str(channelID)))

    async def retrievePoll(self, ctx: commands.Context, guildID: int, pollID: str) -> discord.Message:
        """Retrieves the poll with the given pollID on the given server, returning the message
        object that corresponds to the poll. If poll message has been manually deleted, or channel
        containing poll was deleted, returns None.
        """
        if (not pollID.isnumeric()):
            raise ValueError

        cursor = self.createCursor()
        selectStatement = """SELECT channel_id, message_id FROM polls WHERE server_id = ? AND poll_id = ?"""

        # retrieve the message object from the channelID and messageID and return it
        cursor.execute(selectStatement, (str(guildID), pollID))
        channelID, messageID = cursor.fetchone()
        channel = ctx.guild.get_channel(int(channelID))

        # if channel could not be found by id, then channel has been deleted
        # and poll should be removed from database since it is no longer accessible
        if (channel is None):
            await self.remPoll(guildID, pollID)
            return None

        # if message could not be found in channel, then message has been deleted
        # and poll should be removed from database since it is no longer accessible
        try:
            message = await channel.fetch_message(int(messageID))
        except discord.errors.NotFound:
            await self.remPoll(guildID, pollID)
            return None

        return message
    
    async def getServerPollList(self, guildID: int):
        """Returns list of poll ID numbers for all polls on the given server.
        """
        cursor = self.createCursor()
        selectStatement = """SELECT poll_id FROM polls WHERE server_id = ?"""

        try:
            cursor.execute(selectStatement, (str(guildID),))
            pollList = [pollID[0] for pollID in cursor]
            return pollList
        except TypeError:
            return None

    async def getPollQuestions(self, guildID: int, pollID: str) -> List[str]:
        """Retrieves the list of questions the poll was created with as a list of strings in
        the order they appeared in the poll.
        """
        if (not pollID.isnumeric()):
            raise ValueError

        cursor = self.createCursor()
        selectStatement = """SELECT questions FROM polls WHERE server_id = ? AND poll_id = ?"""

        cursor.execute(selectStatement, (str(guildID), pollID))

        try:
            questions, = cursor.fetchone()
            questionList = questions.split(chr(1))
            return questionList
        except TypeError:
            return None


    ## role_react_msgs table methods ##
    async def addRoleReactMsg(self, guildID: int, channelID: int, messageID: int, roleID: int):
        """Add row pertaining to a react for role message in the role_react_msgs table from
        the given guild, channel, message, and role ID number.
        """
        cursor = self.createCursor()
        insertStatement = """INSERT INTO role_react_msgs(message_id, channel_id, server_id, role_id)
        VALUES(?,?,?,?)
        """

        with self.dbConnection:
            try:
                cursor.execute(insertStatement, (str(messageID), str(channelID), str(guildID), str(roleID)))
            except sqlite3.IntegrityError:
                print("Attempting to add message already in database")

    async def remRoleReactMsg(self, guildID: int, messageID: int):
        """Removes row from role_react_msgs table with the provided guild, channel, and message_id.
        """
        cursor = self.createCursor()
        deleteStatement = """DELETE FROM role_react_msgs WHERE server_id = ? AND channel_id = ? AND message_id = ?"""

        with self.dbConnection:
            cursor.execute(deleteStatement, (str(guildID), str(messageID)))

    async def getRoleIDFromReactMsg(self, guildID: int, messageID: int) -> Optional[int]:
        """Returns a discord Role object corresponding to the role a message should assign, or
        None if no role should be assigned from the messages.
        """
        cursor = self.createCursor()
        selectStatement = """SELECT role_id FROM role_react_msgs WHERE server_id = ? AND message_id = ?"""

        cursor.execute(selectStatement, (str(guildID), str(messageID)))

        try:
            roleID, = cursor.fetchone()
            return int(roleID)
        except TypeError:
            return None


    ## role_invites table methods ##
    async def addRoleInvite(self, guildID: int, inviteID: str, roleID: int):
        """Add row to role_invites table that stores an invite and the role it applies to a user that
        joins with it. 
        """
        if ((guildID is None) or (inviteID is None) or (roleID is None)):
            raise sqlite3.IntegrityError
        elif ((not isinstance(guildID, int)) or (not isinstance(inviteID, str)) or (not isinstance(roleID, int))):
            raise TypeError
        
        cursor = self.createCursor()
        insertStatement = """INSERT INTO role_invites(invite_id, server_id, role_id, uses_count) VALUES(?,?,?,?)"""

        cursor.execute(insertStatement, (inviteID, str(guildID), str(roleID), 0))

    async def remRoleInvite(self, guildID: int, inviteID: str):
        """Removes a row from the  role_invites table corresponding to the given guild and invite ID number. 
        """
        if ((not isinstance(guildID, int)) or (not isinstance(inviteID, str))):
            raise TypeError

        cursor = self.createCursor()
        deleteStatement = """DELETE FROM role_invites WHERE server_id = ? AND invite_id = ?"""

        cursor.execute(deleteStatement, (str(guildID), inviteID))

    async def remAllInvite(self, guildID: int):
        """Removes all rows from the  role_invites table corresponding to the given guild and invite ID number.
        """
        if ((not isinstance(guildID, int))):
            raise TypeError

        cursor = self.createCursor()
        deleteStatement = """DELETE FROM role_invites WHERE server_id = ?"""

        cursor.execute(deleteStatement, (str(guildID),))

    async def getServerRoleInvitesList(self, guildID: int) -> List[Tuple[str, int]]:
        """Gets a list of all role invites on the given server and returns their IDs and the role IDs
        they assign in a list of tuples.
        """
        if (not isinstance(guildID, int)):
            raise TypeError

        cursor = self.createCursor()
        selectStatement = """SELECT invite_id, role_id FROM role_invites WHERE server_id = ?"""

        cursor.execute(selectStatement, (str(guildID),))

        results = cursor.fetchall()
        return results

    async def roleIDFromUsedLink(self, guildID: int, invitesList: List[discord.Invite]):
        """Determines, based on the provided list of invites from the server, what invite has been incremented,
        and as such what role should be applied based on the used invite link.
        """
        if (not isinstance(guildID, int)):
            raise TypeError
        elif (any([not isinstance(val, discord.Invite) for val in invitesList])):
            raise TypeError

        cursor = self.createCursor()
        selectStatement = """SELECT invite_id, uses_count, role_id FROM role_invites WHERE server_id = ?"""

        cursor.execute(selectStatement, (str(guildID),))

        # create dictionary from select statement results, then check which invite in the invites list
        # has a greater use value than what is stored, and return the role id associated with that invite
        inviteUsageDict = {invite_id: (uses_count, role_id) for invite_id, uses_count, role_id in cursor}

        # method for checking if a invite has been incremented, returns false for invites
        # not stored in the role_invites table
        def incrementCheck(invite):
            try:
                return invite.uses > inviteUsageDict[invite.id][0]
            except KeyError:
                return False
        
        usedInvite = discord.utils.find(incrementCheck, invitesList)
        roleID = inviteUsageDict[usedInvite.id][1]

        # increment the uses_count for the used invite
        updateStatement = """UPDATE role_invites SET uses_count = ? WHERE server_id = ? AND invite_id = ?"""
        cursor.execute(updateStatement, (inviteUsageDict[usedInvite.id][0] + 1, str(guildID), usedInvite.id))

        return roleID


    @tasks.loop(minutes=1)
    async def saveDBToFile(self):
        self.dbConnection.commit()

if (__name__ == '__main__'):
    cache = Cache("../data/LocalCache.db")
    cursor = cache.createCursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print(cursor.fetchall())