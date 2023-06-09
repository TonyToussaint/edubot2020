"""Module contains all custom defined exceptions for EduBot"""

from discord.ext.commands.errors import CommandError, BadArgument, MemberNotFound, RoleNotFound

class NotEnoughMembersError(CommandError):
    """Exception raised when a command is invoked requiring a certain
    number of members to exist on the server, such as moving a role or
    grouping by role; and not enough members are present.

    This inherits from :exc:`CommandError`.
    """
    pass

class ServerLockError(CommandError):
    """Exception raised when command to change server lock state
    is invoked when it is already in the state the user is attempting
    to switch to.

    This inherits from :exc:`CommandError`.
    """
    pass

class NotGroupRoleError(BadArgument):
    """Exception raised when command modifying a group role, such as
    renaming or deleting, is given a role that is not cached as a group
    role.

    This inherits from :exc:`BadArgument`.
    """
    pass

class GuildNotInCacheError(KeyError):
    """Exception raised when a given guild ID is not present in the cache that
    is being searched.

    This inherits from :exc:`KeyError`
    """
    pass

class PollNotInCacheError(KeyError):
    """Exception raised when a given poll ID is not present in the poll cache.

    This inherits from :exc:`KeyError`
    """
    pass

class RoleAlreadyInCache(KeyError):
    """Exception raised a role that is trying to be added to the cache already exists
    in the cache.

    This inherits from :exc:`KeyError`
    """
    pass

class RoleNotInCache(KeyError):
    """Exception raised a role that is trying to be removed from the cache doesn't exist
    in the cache.

    This inherits from :exc:`KeyError`
    """
    pass

class PollTooLargeError(ValueError):
    """Exception raised when a poll message would be too long to display.

    This inherits from :exc:`ValueError`
    """
    pass

class TooManyPollAnswers(ValueError):
    """Exception raised when a poll has too many provided answers.

    This inherits from :exc:`ValueError`
    """
    pass

class NoMembersMatchedPattern(BadArgument):
    """Exception raised when no members match the provided regex pattern.
    """
    def __init__(self, argument):
        self.argument = argument
        super().__init__('No members matched the pattern "{}".'.format(argument))

class NoRolesMatchedPattern(BadArgument):
    """Exception raised when no roles match the provided regex pattern.
    """
    def __init__(self, argument):
        self.argument = argument
        super().__init__('No roles matched the pattern "{}".'.format(argument))