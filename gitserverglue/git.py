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

from zope.interface import implements
from twisted.python import log

from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ProcessProtocol, Factory
from twisted.internet.interfaces import IPushProducer

from gitserverglue.common import git_packet


class GitProcessProtocol(ProcessProtocol):
    def __init__(self, gitprotocol):
        self.gitprotocol = gitprotocol

    def connectionMade(self):
        # twisted.internet.process.Process seems to not fully
        # implement IPushProducer since stopProducing is missing
        # therefore patch in a dummy one
        if not hasattr(self.transport, "stopProducing"):
            setattr(self.transport, "stopProducing",
                    lambda: self.transport.loseConnection())

        self.transport.registerProducer(self.gitprotocol, True)
        self.gitprotocol.transport.registerProducer(self.transport, True)

        self.gitprotocol.resumeProducing()

    def outReceived(self, data):
        self.gitprotocol.transport.write(data)

    def errReceived(self, data):
        self.gitprotocol.transport.write(data)

    def processEnded(self, status):
        log.msg("Git ended with %r" % status)
        self.gitprotocol.transport.unregisterProducer()
        self.gitprotocol.transport.loseConnection()


class GitProtocol(Protocol):
    implements(IPushProducer)

    __buffer = ''
    paused = False
    requestReceived = False

    def __init__(self, authnz, git_configuration):
        self.authnz = authnz
        self.git_configuration = git_configuration

    def dataReceived(self, data):
        self.__buffer = self.__buffer + data

        while not self.paused and len(self.__buffer) >= 4:
            try:
                pktlen = int(self.__buffer[:4], 16)
            except ValueError:
                return self.sendErrorAndDisconnect(
                    "ERR Invalid Paket Length: " + self.__buffer[:4])

            if pktlen == 0:  # flush packet 0000
                pktlen = 4

            # The git protocol specifies bounds for the packet length
            if pktlen < 4 or pktlen > 65524:
                return self.sendErrorAndDisconnect(
                    "ERR Invalid Paket Length: " + self.__buffer[:4])

            # Do we have the complete packet in the buffer?
            if pktlen > len(self.__buffer):
                return

            packet = self.__buffer[:pktlen]
            self.__buffer = self.__buffer[pktlen:]
            self.packetReceived(packet)

    def packetReceived(self, data):
        if not self.requestReceived:
            payload = data[4:]

            # git:// would also support other RPC methods, but since
            # there is no authentication, only allow cloning aka
            # git-upload-pack
            if not payload.startswith("git-upload-pack"):
                return self.sendErrorAndDisconnect(
                    "ERR Request not supported. "
                    "Only git-upload-pack will be accepted")

            try:
                rpc_params = payload[len("git-upload-pack "):].split("\0")
                path, unused_host, unused_eol = rpc_params
            except ValueError:
                return self.sendErrorAndDisconnect(
                    "ERR Unable to parse request line")

            path_info = self.git_configuration.path_lookup(path,
                                                           protocol_hint='git')
            if path_info is None or path_info['repository_fs_path'] is None:
                return self.sendErrorAndDisconnect("ERR Repository not found")

            if not self.authnz.can_read(None, path_info):
                return self.sendErrorAndDisconnect(
                    "ERR Repository does not allow anonymous read access")

            # wait with data until we have a connection to the process
            self.pauseProducing()
            self.requestReceived = True
            self.process = GitProcessProtocol(self)

            gitbinary = self.git_configuration.git_binary
            cmdargs = ['git', 'upload-pack', path_info['repository_fs_path']]
            log.msg("Spawning %s with args %r" % (gitbinary, cmdargs))
            reactor.spawnProcess(self.process, gitbinary, cmdargs)

        else:
            self.process.transport.write(data)

    def sendErrorAndDisconnect(self, msg):
        self.transport.write(git_packet(msg))
        self.transport.loseConnection()

        # return None so it can be used
        # in a return statement in dataReceived for simplicity
        return None

    # IPushProducer
    def pauseProducing(self):
        self.paused = True
        self.transport.pauseProducing()

    def resumeProducing(self):
        self.paused = False
        self.transport.resumeProducing()
        self.dataReceived('')

    def stopProducing(self):
        # Only pause and don't call self.transport.stopProducing
        # since stopProducing will call loseConnection. This
        # can happen when git closes stdin but there is still
        # data on stdout/stderr
        # loseConnection will be called when the process ends
        # and everything has been written
        self.paused = True


class GitFactory(Factory):
    def __init__(self, authnz, git_configuration):
        self.authnz = authnz
        self.git_configuration = git_configuration

    def buildProtocol(self, addr):
        return GitProtocol(self.authnz, self.git_configuration)


def create_factory(authnz, git_configuration):
    return GitFactory(authnz, git_configuration)
