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

from urllib import unquote
import string

from twisted.internet.interfaces import IConsumer
from twisted.web.http import HTTPChannel, parse_qs, datetimeToString
from twisted.web.server import Request, version
from twisted.web.resource import IResource, getChildForRequest
from twisted.web.util import DeferredResource
from twisted.python import failure


class StreamingRequest(Request):
    """Modified Request to support streaming content"""

    _fallbackToBuffered = True
    fallbackContentTypes = [
        'multipart/form-data',
        'application/x-www-form-urlencoded'
    ]

    def requestHeadersReceived(self, command, path, version):
        """Called when a StreamingHTTPChannel received all headers

        If the method was POST and we have a content type listed
        in self.fallbackContentTypes, fallback mode will stay
        enabled and everything works just like in vanilla twisted.

        However, if these conditions are not met, streaming
        mode will be used."""

        ctype = self.requestHeaders.getRawHeaders('content-type')
        if ctype is not None:
            ctype = ctype[0]
        if command == "POST" and ctype in self.fallbackContentTypes:
            return  # stay in fallback mode

        if command not in ["POST", "PUT"]:
            return  # stay in fallback mode except for POST and PUT

        self._fallbackToBuffered = False

        # the following code will perform the same steps as
        # the vanilla requestReceived minus content parsing
        self.args = {}
        self.stack = []

        self.method, self.uri = command, path
        self.clientproto = version
        x = self.uri.split('?', 1)

        if len(x) == 1:
            self.path = self.uri
        else:
            self.path, argstring = x
            self.args = parse_qs(argstring, 1)

        # cache the client and server information, we'll need this later to be
        # serialized and sent with the request so CGIs will work remotely
        self.client = self.channel.transport.getPeer()
        self.host = self.channel.transport.getHost()

        self.process()

    def requestReceived(self, command, path, version):
        if self._fallbackToBuffered:
            Request.requestReceived(self, command, path, version)
        else:
            self.resource.unregisterProducer()

    def process(self):
        if self._fallbackToBuffered:
            return Request.process(self)

        # streaming mode
        # pause producing on channel until we know what resource
        # we deal with
        self.channel.transport.pauseProducing()
        self.site = self.channel.site

        self.setHeader('server', version)
        self.setHeader('date', datetimeToString())

        self.prepath = []
        self.postpath = map(unquote, string.split(self.path[1:], '/'))

        try:
            self.processResource(self.site.getResourceFor(self))
        except:
            self.processingFailed(failure.Failure())

    def processResource(self, resource):
        if not isinstance(resource, DeferredResource):
            resource = getChildForRequest(resource, self)

        if isinstance(resource, DeferredResource):
            resource.d.addCallback(self.processResource).addErrback(
                self.processingFailed)
        else:
            self.resource = self._getRealResource(resource)

            if IConsumer.providedBy(self.resource):
                self.resource.registerProducer(self.channel.transport, True)
                self.render(resource)  # use resource here to not break proxies
            else:
                self._fallbackToBuffered = True

            # resource is determined, resume producing
            self.channel.transport.resumeProducing()

    def _getRealResource(self, resource):
        proxied = False
        for b in resource.__class__.__bases__:
            if b.__name__ == '(Proxy for twisted.web.resource.IResource)':
                proxied = True

        if not proxied:
            return resource

        # find the real resource (or the next proxy)
        for x in vars(resource).values():
            if IResource.providedBy(x):
                return self._getRealResource(x)

        raise Exception("Unable to find real resource")

    def handleContentChunk(self, data):
        if self._fallbackToBuffered:
            self.content.write(data)
        else:
            self.resource.write(data)


class StreamingHTTPChannel(HTTPChannel):
    """Modified HTTPChannel to support streaming requests"""

    def allHeadersReceived(self):
        HTTPChannel.allHeadersReceived(self)
        req = self.requests[-1]
        if hasattr(req, "requestHeadersReceived"):
            req.requestHeadersReceived(self._command,
                                       self._path, self._version)


def make_site_streaming(site):
    site.requestFactory = StreamingRequest
    site.protocol = StreamingHTTPChannel

    return site
