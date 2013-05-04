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

import os.path
import re
import datetime
import calendar
import email.utils

from zope.interface import implements
from twisted.python import log

from twisted.internet import reactor, defer, task
from twisted.internet.interfaces import IProcessProtocol, IPushProducer, IConsumer

from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import AllowAnonymousAccess, ANONYMOUS
from twisted.web.guard import HTTPAuthSessionWrapper, BasicCredentialFactory
from twisted.web._auth.wrapper import UnauthorizedResource

from twisted.web.static import File
from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.resource import Resource, IResource, NoResource, ForbiddenResource

from twistedgit.common import PasswordChecker, git_packet
from twistedgit.streamingweb import StreamingRequest


def get_date_header(dt=None):
    if dt is None:
        dt = datetime.datetime.now()
    t = calendar.timegm(dt.utctimetuple())
    return email.utils.formatdate(t, localtime=False, usegmt=True)

cache_forever = lambda: [('Expires', get_date_header(datetime.datetime.now() + datetime.timedelta(days=365))),
                 ('Pragma', 'no-cache'),
                 ('Cache-Control', 'public, max-age=31556926')]

dont_cache = lambda: [('Expires', 'Fri, 01 Jan 1980 00:00:00 GMT'),
              ('Pragma', 'no-cache'),
              ('Cache-Control', 'no-cache, max-age=0, must-revalidate')]

file_headers = {
    re.compile('.*/(HEAD)$'):                                   lambda: dict(dont_cache() + [('Content-Type', 'text/plain')]),
    re.compile('.*/(objects/info/alternates)$'):                lambda: dict(dont_cache() + [('Content-Type', 'text/plain')]),
    re.compile('.*/(objects/info/http-alternates)$'):           lambda: dict(dont_cache() + [('Content-Type', 'text/plain')]),
    re.compile('.*/(objects/info/packs)$'):                     lambda: dict(dont_cache() + [('Content-Type', 'text/plain; charset=utf-8')]),
    re.compile('.*/(objects/info/[^/]+)$'):                     lambda: dict(dont_cache() + [('Content-Type', 'text/plain')]),
    re.compile('.*/(objects/[0-9a-f]{2}/[0-9a-f]{38})$'):       lambda: dict(cache_forever() + [('Content-Type', 'application/x-git-loose-object')]),
    re.compile('.*/(objects/pack/pack-[0-9a-f]{40}\\.pack)$'):  lambda: dict(cache_forever() + [('Content-Type', 'application/x-git-packed-objects')]),
    re.compile('.*/(objects/pack/pack-[0-9a-f]{40}\\.idx)$'):   lambda: dict(cache_forever() + [('Content-Type', 'application/x-git-packed-objects-toc')]),
}


class FileLikeProducer(object):
    """twisted.web.client.FileBodyProducer adaptation for request.content"""
    implements(IPushProducer)

    def __init__(self, inputFile, consumer=None, cooperator=task, readSize=2 ** 16):
        self._inputFile = inputFile
        self._cooperate = cooperator.cooperate
        self._readSize = readSize
        self._consumer = consumer
        self._task = None

    def stopProducing(self):
        try:
            self._task.stop()
        except:
            pass

    def startProducing(self, consumer=None):
        if consumer is not None:
            self._consumer = consumer

        if self._task is not None:
            raise Exception("Already started")

        self._createTask()

    def pauseProducing(self):
        self._task.pause()

    def resumeProducing(self):
        if self._task is None:
            self._createTask()
        self._task.resume()

    def _createTask(self):
        if self._consumer is None:
            raise Exception("No consumer")

        self._task = self._cooperate(self._writeloop(self._consumer))
        d = self._task.whenDone()

        def maybeStopped(reason):
            reason.trap(task.TaskStopped)
            return defer.Deferred()

        d.addCallbacks(lambda ignored: None, maybeStopped)
        return d

    def _writeloop(self, consumer):
        while True:
            bytes = self._inputFile.read(self._readSize)
            if not bytes:
                break
            consumer.write(bytes)
            yield None


class GitCommand(Resource):
    """A resource returning content from a git process"""
    implements(IProcessProtocol, IConsumer)

    isLeaf = True
    process = None
    _producer = None

    def __init__(self, cmd, args):
        self.cmd = cmd
        self.args = args

    # Resource
    def render(self, request):
        self.request = request
        reactor.spawnProcess(self, self.cmd, self.args)

        return NOT_DONE_YET

    # IProcessProtocol
    def makeConnection(self, process):
        self.process = process

        # twisted.internet.process.Process seems to not fully
        # implement IPushProducer since stopProducing is missing
        # therefore patch in a dummy one
        if not hasattr(process, "stopProducing"):
            setattr(process, "stopProducing",
                    lambda: process.loseConnection())

        self.request.registerProducer(process, True)

        if not isinstance(self.request, StreamingRequest):
            # twisted default request, does not support streaming contents
            producer = FileLikeProducer(self.request.content, process)
            producer.startProducing()
            process.registerProducer(producer, True)

        elif self._producer is not None:
            self._producer.resumeProducing()
            self.process.registerProducer(self._producer, True)

    def childDataReceived(self, childFD, data):
        self.request.write(data)

    def childConnectionLost(self, childFD):
        pass

    def processExited(self, reason):
        pass

    def processEnded(self, reason):
        self.request.unregisterProducer()
        self.request.finish()

    # IConsumer for StreamingRequest
    def registerProducer(self, producer, streaming):
        # suppress original stopProducing since git will
        # call it on closing stdin -> httpchannel gets closed
        # because the original stopProducing calls loseConnection
        def suppressedStop(self):
            # Do not pause producing here unless you make sure
            # producing is resumed upon request completion. Otherwise,
            # no further requests will be received in keep-alive!
            pass  # self.pauseProducing()
        suppressedStop.original = producer.stopProducing
        producer.stopProducing = suppressedStop.__get__(producer, producer.__class__)

        if self.process is None:
            producer.pauseProducing()
            self._producer = producer
        else:
            self.process.registerProducer(producer)

    def unregisterProducer(self):
        if self.process:
            self.process.closeStdin()

    def write(self, data):
        self.process.write(data)


class InfoRefs(Resource):
    """Resource for handling git requests to /info/refs"""
    isLeaf = True

    def __init__(self, gitpath, gitcommand='git'):
        self.gitpath = gitpath
        self.gitcommand = gitcommand

    def render_GET(self, request):
        if 'service' not in request.args:
            # dumb client
            for key, val in dont_cache():
                request.setHeader(key, val)

            log.msg('Dumb client, sending %s' % os.path.join(self.gitpath, 'info', 'refs'))
            return File(os.path.join(self.gitpath, 'info', 'refs'), 'text/plain; charset=utf-8').render_GET(request)

        else:
            # smart client
            if request.args['service'][0] not in ['git-upload-pack', 'git-receive-pack']:
                return "Invalid RPC: " + request.args['service'][0]

            rpc = request.args['service'][0][4:]
            request.write(git_packet('# service=git-' + rpc) + git_packet())
            cmd = self.gitcommand
            args = [os.path.basename(cmd), rpc, '--stateless-rpc', '--advertise-refs', self.gitpath]

            return GitCommand(cmd, args).render(request)


class GitResource(Resource):
    """Resource representing a git repository"""

    def __init__(self, username, authnz, git_configuration, credentialFactories):
        Resource.__init__(self)

        self.username = username
        self.authnz = authnz
        self.git_configuration = git_configuration
        self.credentialFactories = credentialFactories

    def getChild(self, path, request):
        """Find the appropriate child resource depending on request type

        Possible URLs:
        - /foo/bar/info/refs -> info refs (file / SmartHTTP hybrid)
        - /foo/bar/git-upload-pack -> SmartHTTP RPC
        - /foo/bar/git-receive-pack -> SmartHTTP RPC
        - /foo/bar/HEAD -> file (dumb http)
        - /foo/bar/objects/* -> file (dumb http)
        """
        path = request.path  # alternatively use path + request.postpath
        pathparts = path.split('/')
        writerequired = False
        gitpath = script_name = new_path = None
        resource = NoResource()

        # Path lookup / translation
        gitpath = self.git_configuration.translate_path(path)
        if gitpath is None:
            log.msg('User %s tried to access %s but the translator did not return a real path' % (self.username, path))
            return resource

        if hasattr(self.git_configuration, 'split_path'):
            script_name, new_path = self.git_configuration.split_path(path)

        log.msg('Resolved %s to %s with splitting %s :: %s' % (path, gitpath, script_name, new_path))

        # since pretty much everything needs read access, check for it now
        if not self.authnz.can_read(self.username, script_name):
            if self.username is None:
                return UnauthorizedResource(self.credentialFactories)
            else:
                return ForbiddenResource("You don't have read access")

        # Smart HTTP requests
        if len(pathparts) >= 2 and pathparts[-2] == 'info' and pathparts[-1] == 'refs':
            if 'service' in request.args and request.args['service'][0] == 'git-receive-pack':
                writerequired = True
            resource = InfoRefs(gitpath)

        elif len(pathparts) >= 1 and pathparts[-1] == 'git-upload-pack':
            cmd = 'git'
            args = [os.path.basename(cmd), 'upload-pack', '--stateless-rpc', gitpath]
            resource = GitCommand(cmd, args)
            request.setHeader('Content-Type', 'application/x-git-upload-pack-result')

        elif len(pathparts) >= 1 and pathparts[-1] == 'git-receive-pack':
            writerequired = True
            cmd = 'git'
            args = [os.path.basename(cmd), 'receive-pack', '--stateless-rpc', gitpath]
            resource = GitCommand(cmd, args)
            request.setHeader('Content-Type', 'application/x-git-receive-pack-result')

        # static files or webfrontend
        else:
            # determine the headers for this file
            filename, headers = None, None
            for matcher, get_headers in file_headers.items():
                m = matcher.match(path)
                if m:
                    filename = m.group(1)
                    headers = get_headers()
                    break

            # if we have a match, serve the file with the appropriate headers or fallback to webfrontend
            if filename is None:
                # TODO: webfrontend support
                pass
            else:
                for key, val in headers.items():
                    request.setHeader(key, val)

                log.msg("Returning file %s" % os.path.join(gitpath, filename))
                resource = File(os.path.join(gitpath, filename), headers['Content-Type'])
                resource.isLeaf = True  # we are always going straight to the file, so skip further resource tree traversal

        # before returning the resource, check if write access is required and enforce privileges accordingly
        # anonymous (username = None) will never be granted write access
        if writerequired and (self.username is None or not self.authnz.can_write(self.username, script_name)):
            if self.username is None:
                return UnauthorizedResource(self.credentialFactories)
            else:
                return ForbiddenResource("You don't have write access")

        return resource

    def render_GET(self, request):
        return ForbiddenResource()


class GitHTMLRealm(object):
    implements(IRealm)

    def __init__(self, authnz, git_configuration, credentialFactories):
        self.authnz = authnz
        self.git_configuration = git_configuration
        self.credentialFactories = credentialFactories

    def requestAvatar(self, avatarId, mind, *interfaces):
        if avatarId == ANONYMOUS:
            avatarId = None  # anonymous

        if IResource in interfaces:
            return IResource, GitResource(avatarId, self.authnz, self.git_configuration, self.credentialFactories), lambda: None
        raise NotImplementedError()


def create_factory(authnz, git_configuration):
    credentialFactories = [BasicCredentialFactory('Git Repositories')]
    gitportal = Portal(GitHTMLRealm(authnz, git_configuration, credentialFactories))

    if hasattr(authnz, 'check_password'):
        log.msg("Registering PasswordChecker")
        gitportal.registerChecker(PasswordChecker(authnz.check_password))
    gitportal.registerChecker(AllowAnonymousAccess())

    resource = HTTPAuthSessionWrapper(gitportal, credentialFactories)
    site = Site(resource)

    return site
