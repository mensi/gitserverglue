# -*- coding: utf-8 -*-
#
# Copyright 2011 Manuel Stocker <mensi@mensi.ch>
#
# This file is part of TwistedGit.
#
# TwistedGit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# TwistedGit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TwistedGit.  If not, see http://www.gnu.org/licenses

from twisted.cred import portal, checkers, credentials
from twisted.conch import error, avatar
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.conch.ssh import factory, userauth, connection, keys, session
from twisted.internet import reactor, protocol, defer
from twisted.python import log, failure
from zope.interface import implements
import sys, shlex

class GitAvatar(avatar.ConchUser):
    def __init__(self, username, authnz, git_configuration):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.authnz = authnz
        self.git_configuration = git_configuration
        self.channelLookup.update({'session':session.SSHSession})

class GitRealm:
    implements(portal.IRealm)

    def __init__(self, authnz, git_configuration):
        self.authnz = authnz
        self.git_configuration = git_configuration

    def requestAvatar(self, avatarId, mind, *interfaces):
        return interfaces[0], GitAvatar(avatarId, self.authnz, self.git_configuration), lambda: None

class GitSession:

    def __init__(self, avatar):
        self.avatar = avatar

    def execCommand(self, proto, cmd):
        cmdparts = shlex.split(cmd)
        rpc = cmdparts[0]
        path = cmdparts[-1]
        if rpc not in ['git-upload-pack', 'git-receive-pack']:
            log.err('Unknown RPC: ' + rpc)
            return self._kill_connection(proto, "Unknown RPC")

        if (rpc == 'git-upload-pack' and not self.avatar.authnz.can_read(self.avatar.username, path)):
            log.msg('User %s tried to access %s but does not have read permissions' % (self.avatar.username, path))
            return self._kill_connection(proto, "You don't have read permissions")

        if (rpc == 'git-receive-pack' and not self.avatar.authnz.can_write(self.avatar.username, path)):
            log.msg('User %s tried to access %s but does not have write permissions' % (self.avatar.username, path))
            return self._kill_connection(proto, "You don't have write permissions")

        realpath = self.avatar.git_configuration.translate_path(path)
        gitshell = self.avatar.git_configuration.git_shell_binary
        if realpath is None:
            return self._kill_connection(proto, "Unknown Repository")
        else:
            log.msg("Spawning %s with args %r" % (gitshell, ['git-shell', '-c', rpc + ' \'' + realpath + '\'']))
            reactor.spawnProcess(proto, gitshell, ['git-shell', '-c', rpc + ' \'' + realpath + '\''])

    def getPty(self, term, windowSize, attrs):
        pass

    def openShell(self, trans):
        self._kill_connection(trans, "Shell access not allowed\n")

    def _kill_connection(self, trans, msg):
        class DummyTransport:
            def loseConnection(self):
                pass

        trans.makeConnection(DummyTransport())
        trans.write(msg)
        trans.loseConnection()

    def eofReceived(self):
        pass

    def closed(self):
        pass

from twisted.python import components
components.registerAdapter(GitSession, GitAvatar, session.ISession)

class PublicKeyChecker(SSHPublicKeyDatabase):
    def __init__(self, checker):
        self.checker = checker

    def checkKey(self, credentials):
        return defer.maybeDeferred(self.checker, credentials.username, credentials.blob)

class PasswordChecker:

    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword,)

    def __init__(self, checker):
        self.checker = checker

    def _cbPasswordMatch(self, matched, username):
        if matched:
            return defer.succeed(username)
        else:
            return failure.Failure(error.UnauthorizedLogin())

    def requestAvatarId(self, credentials):
        return defer.maybeDeferred(self.checker, credentials.username, credentials.password).addCallback(
            self._cbPasswordMatch, str(credentials.username))

def create_factory(private_keys, public_keys, authnz, git_configuration):
    class GitSSHFactory(factory.SSHFactory):
        publicKeys = public_keys
        privateKeys = private_keys

    gitportal = portal.Portal(GitRealm(authnz, git_configuration))

    if hasattr(authnz, 'check_password'):
        log.msg("Registering PasswordChecker")
        gitportal.registerChecker(PasswordChecker(authnz.check_password))
    if hasattr(authnz, 'check_publickey'):
        log.msg("Registering PublicKeyChecker")
        gitportal.registerChecker(PublicKeyChecker(authnz.check_publickey))

    GitSSHFactory.portal = gitportal

    return GitSSHFactory
