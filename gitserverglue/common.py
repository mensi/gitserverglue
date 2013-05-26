# -*- coding: utf-8 -*-
#
# Copyright 2011 Manuel Stocker <mensi@mensi.ch>
#
# This file is part of GitServerGlue.
#
# GitServerGlue is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GitServerGlue is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GitServerGlue.  If not, see http://www.gnu.org/licenses

from twisted.cred import checkers, credentials, error
from twisted.internet import defer
from twisted.internet.error import ProcessTerminated
from twisted.internet.interfaces import IProcessTransport
from twisted.python.failure import Failure
from zope.interface import implements


def git_packet(data=None):
    """Format data as a git pktline

    If data is None, a flush packet will be returned"""
    if data is None:
        return '0000'
    return str(hex(len(data) + 4)[2:].rjust(4, '0')) + data


class ErrorProcess(object):
    """Simulates a process transport with a message on stderr

    Implements an IProcessTransport that simulates process
    termination with the given return code and writing
    a message to stderr. Properly closes child FDs.
    """
    implements(IProcessTransport)

    def __init__(self, proto, code, message):
        proto.makeConnection(self)
        proto.childDataReceived(2, message + '\n')

        proto.childConnectionLost(0)
        proto.childConnectionLost(1)
        proto.childConnectionLost(2)

        failure = Failure(ProcessTerminated(code))

        proto.processExited(failure)
        proto.processEnded(failure)

        # ignore all unused methods
        noop = lambda *args, **kwargs: None
        self.closeStdin = noop
        self.closeStdout = noop
        self.closeStderr = noop
        self.writeToChild = noop
        self.loseConnection = noop
        self.signalProcess = noop


class PasswordChecker:

    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword,)

    def __init__(self, checker):
        self.checker = checker

    def _cbPasswordMatch(self, matched, username):
        if matched:
            return defer.succeed(username)
        else:
            return Failure(error.UnauthorizedLogin())

    def requestAvatarId(self, credentials):
        return defer.maybeDeferred(
           self.checker,
           credentials.username,
           credentials.password
        ).addCallback(self._cbPasswordMatch, str(credentials.username))
